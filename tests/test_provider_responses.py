"""Provider adapters must never treat missing or blank data as publishable content."""
import sys
from types import SimpleNamespace

import pytest

from pennovia.voice import generator
from pennovia.voice.analyzer import VoiceProfile


PROFILE = VoiceProfile(language="en")

def _mock_ollama_session(monkeypatch, response_fn, exception_type):
    """Assert local inference cannot inherit proxy or netrc configuration."""
    class Session:
        def __init__(self):
            self.trust_env = True

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def post(self, url, *, json, timeout):
            assert self.trust_env is False
            assert url == "http://127.0.0.1:11434/api/chat"
            assert timeout == 300
            assert json["stream"] is False
            return response_fn()

    monkeypatch.setitem(
        sys.modules, "requests",
        SimpleNamespace(Session=Session, RequestException=exception_type),
    )



def test_blank_and_nontext_responses_are_not_drafts():
    for value in (None, "", "   ", [], {}):
        with pytest.raises(RuntimeError, match="no usable draft"):
            generator._require_draft(value, "Mock")
    assert generator._require_draft("  Draft  ", "Mock") == "Draft"


def test_ollama_rejects_empty_and_malformed_json(monkeypatch):
    class FakeRequestError(Exception):
        pass
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {"message": {"content": "   "}}

    _mock_ollama_session(monkeypatch, Response, FakeRequestError)
    with pytest.raises(RuntimeError, match="no usable draft"):
        generator.generate_ollama(PROFILE, "story", "Topic")


def test_ollama_network_failure_is_actionable_without_echoing_secrets(monkeypatch):
    class FakeRequestError(Exception):
        pass
    def fail(*args, **kwargs):
        raise FakeRequestError("authorization-token-secret")
    _mock_ollama_session(monkeypatch, fail, FakeRequestError)
    with pytest.raises(RuntimeError, match="Ollama request failed") as exc:
        generator.generate_ollama(PROFILE, "story", "Topic")
    assert "authorization-token-secret" not in str(exc.value)



def test_local_ollama_never_uses_ambient_proxy_settings(monkeypatch):
    monkeypatch.setenv("HTTP_PROXY", "http://proxy.invalid:8080")
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.invalid:8080")
    monkeypatch.delenv("NO_PROXY", raising=False)
    monkeypatch.delenv("no_proxy", raising=False)

    class FakeRequestError(Exception):
        pass

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"message": {"content": "Private local draft"}}

    _mock_ollama_session(monkeypatch, Response, FakeRequestError)
    assert generator.generate_ollama(PROFILE, "story", "Topic") == "Private local draft"

def test_openrouter_malformed_reply_is_rejected(monkeypatch):
    class FakeRequestError(Exception):
        pass
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {"choices": []}
    monkeypatch.setitem(
        sys.modules, "requests",
        SimpleNamespace(post=lambda *a, **kw: Response(), RequestException=FakeRequestError),
    )
    with pytest.raises(RuntimeError, match="invalid response structure"):
        generator.generate_openrouter(PROFILE, "story", "Topic", api_key="fake")


def test_openai_none_content_is_rejected(monkeypatch):
    def fake_client(**kwargs):
        return SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(
                create=lambda **kw: SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content=None))]
                )
            ))
        )
    monkeypatch.setitem(
        sys.modules, "openai",
        SimpleNamespace(OpenAI=fake_client, OpenAIError=Exception),
    )
    with pytest.raises(RuntimeError, match="no usable draft"):
        generator.generate_openai(PROFILE, "story", "Topic", api_key="fake")


def test_anthropic_joins_text_blocks_and_skips_nontext(monkeypatch):
    def fake_client(**kwargs):
        return SimpleNamespace(messages=SimpleNamespace(create=lambda **kw: SimpleNamespace(
            content=[
                SimpleNamespace(type="tool_use", text=None),
                SimpleNamespace(type="text", text="First part."),
                SimpleNamespace(type="text", text="Second part."),
            ]
        )))
    monkeypatch.setitem(
        sys.modules, "anthropic",
        SimpleNamespace(Anthropic=fake_client, AnthropicError=Exception),
    )
    assert generator.generate_anthropic(PROFILE, "story", "Topic", api_key="fake") == "First part.\nSecond part."


def test_auto_does_not_hide_programming_errors_as_missing_backend(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def raise_unexpected(*args, **kwargs):
        raise TypeError("Unexpected programming error")

    monkeypatch.setattr(generator, "generate_ollama", raise_unexpected)
    with pytest.raises(TypeError, match="Unexpected programming error"):
        generator.generate(PROFILE, "story", "Topic", backend="auto")


def test_ollama_optional_token_budget_is_bounded_and_sent_to_local_model(monkeypatch):
    for invalid in (0, 63, 8193, -1, True, 64.5, "640"):
        with pytest.raises(ValueError, match="max_tokens"):
            generator.generate_ollama(PROFILE, "story", "Topic", max_tokens=invalid)

    class FakeRequestError(Exception):
        pass

    class Session:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def post(self, url, **kwargs):
            assert self.trust_env is False
            assert url == "http://127.0.0.1:11434/api/chat"
            assert kwargs["json"]["options"] == {"num_predict": 640}
            return SimpleNamespace(
                raise_for_status=lambda: None,
                json=lambda: {"message": {"content": "A complete local draft."}},
            )

    monkeypatch.setitem(
        sys.modules, "requests",
        SimpleNamespace(Session=Session, RequestException=FakeRequestError),
    )
    result = generator.generate_ollama(PROFILE, "story", "Topic", max_tokens=640)
    assert result == "A complete local draft."

    for invalid in (-1, 2_147_483_648, True, "23", 3.5):
        with pytest.raises(ValueError, match="seed"):
            generator.generate_ollama(PROFILE, "story", "Topic", seed=invalid)




@pytest.mark.parametrize(
    ("reason", "expected"),
    [("stop", "complete"), ("length", "truncated"), (None, "unknown"),
     ("invalid", "unknown"), (37, "unknown")],
)
def test_ollama_optional_receipt_preserves_generation_completion(monkeypatch, reason, expected):
    class FakeRequestError(Exception):
        pass

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "message": {"content": "  An editable draft that can be kept.  "},
                "done": True,
                "done_reason": reason,
                "prompt_eval_count": 250,
                "eval_count": 640,
            }

    _mock_ollama_session(monkeypatch, Response, FakeRequestError)
    # Existing public API still returns only a text draft.
    assert generator.generate_ollama(PROFILE, "story", "Topic") == (
        "An editable draft that can be kept."
    )
    receipt = generator.generate_ollama(
        PROFILE, "story", "Topic", return_metadata=True
    )
    assert isinstance(receipt, generator.OllamaGeneration)
    assert receipt.text == "An editable draft that can be kept."
    assert receipt.completion_status == expected
    assert receipt.done_reason == (reason if reason in ("stop", "length") else None)
    assert receipt.prompt_tokens == 250
    assert receipt.generated_tokens == 640


def test_ollama_untrusted_token_usage_never_creates_fake_counts():
    result = generator._ollama_receipt({
        "message": {"content": "Draft"},
        "done": True,
        "done_reason": "stop",
        "prompt_eval_count": True,
        "eval_count": "500",
    })
    assert result.completion_status == "complete"
    assert result.prompt_tokens is None
    assert result.generated_tokens is None
    with pytest.raises(RuntimeError, match="invalid response"):
        generator._ollama_receipt(None)
    with pytest.raises(RuntimeError, match="invalid response"):
        generator._ollama_receipt({"message": []})


def test_auto_local_metadata_and_cloud_backwards_compatibility(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    calls = []
    def local(*args, **kwargs):
        calls.append(kwargs)
        if kwargs.get("return_metadata"):
            return generator.OllamaGeneration("Draft", "truncated", "length", 100, 64)
        return "Draft"

    monkeypatch.setattr(generator, "generate_ollama", local)
    assert generator.generate(PROFILE, "story", "Topic", backend="auto") == "Draft"
    receipt = generator.generate(
        PROFILE, "story", "Topic", backend="auto", return_metadata=True
    )
    assert receipt.completion_status == "truncated"
    assert calls == [{}, {"return_metadata": True}]


def test_ollama_does_not_certify_done_reason_without_true_done_flag():
    receipt = generator._ollama_receipt({
        "message": {"content": "Text"},
        "done_reason": "stop",
        "eval_count": 12,
    })
    assert receipt.completion_status == "unknown"
    receipt = generator._ollama_receipt({
        "message": {"content": "Text"},
        "done": False,
        "done_reason": "stop",
    })
    assert receipt.completion_status == "unknown"
    assert receipt.done_reason == "stop"


def test_valid_local_seed_is_sent_only_to_ollama_request(monkeypatch):
    class FakeRequestError(Exception):
        pass

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"message": {"content": "Seeded draft."}, "done": True,
                    "done_reason": "stop"}

    def response_with_seed():
        return Response()

    def session_factory():
        class Session:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def post(self, url, **kwargs):
                assert not self.trust_env
                assert kwargs["json"]["options"] == {
                    "num_predict": 640, "seed": 123456
                }
                return response_with_seed()
        return Session()

    monkeypatch.setitem(
        sys.modules, "requests",
        SimpleNamespace(Session=session_factory, RequestException=FakeRequestError),
    )
    receipt = generator.generate_ollama(
        PROFILE, "story", "Topic", max_tokens=640, seed=123456,
        return_metadata=True,
    )
    assert receipt.completion_status == "complete"
