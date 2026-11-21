"""Ollama completion uncertainty must survive Studio generation and review."""
import pytest

from pennovia.studio import server
from pennovia.voice import generator
from pennovia.voice.analyzer import VoiceProfile


PROFILE = VoiceProfile(
    language="en", text_count=1, total_words=350,
    avg_sentence_words=12.0, avg_paragraph_sentences=2.0,
)


@pytest.mark.parametrize(
    ("status", "reason", "expected_issue"),
    [
        ("complete", "stop", None),
        ("truncated", "length", "generation_truncated"),
        ("unknown", None, "generation_completion_unknown"),
    ],
)
def test_studio_generation_receipt_never_approves_known_incomplete_drafts(
    monkeypatch, status, reason, expected_issue,
):
    draft = ("The traveler crossed the square and saw the morning light. "
             "This was an ordinary fictional day in an unnamed town. ") * 22

    def fake_generate(*args, **kwargs):
        assert kwargs["return_metadata"] is True
        assert kwargs["backend"] == "ollama"
        return generator.OllamaGeneration(
            draft, status, reason, prompt_tokens=300, generated_tokens=640,
        )

    monkeypatch.setattr(generator, "generate", fake_generate)
    out = server._generate_request({
        "topic": "Fictional scene", "content_type": "story",
        "backend": "ollama", "model": "",
    }, PROFILE)
    assert out["draft"] == draft
    assert out["generation"]["completion_status"] == status
    assert out["generation"]["generated_tokens"] == 640
    if expected_issue:
        assert not out["review"]["passed"]
        assert expected_issue in out["review"]["issues"]
    else:
        assert "generation_truncated" not in out["review"]["issues"]
        assert "generation_completion_unknown" not in out["review"]["issues"]


def test_studio_mocked_non_ollama_provider_preserves_existing_text_contract(monkeypatch):
    def fake_generate(*args, **kwargs):
        assert "return_metadata" not in kwargs
        return "A short editable draft."

    monkeypatch.setattr(generator, "generate", fake_generate)
    out = server._generate_request({
        "topic": "A thought", "content_type": "story",
        "backend": "codex", "model": "",
    }, PROFILE)
    assert out["draft"] == "A short editable draft."
    assert "generation" not in out
