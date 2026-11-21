"""Offline, deterministic safeguards for the public, paired live-model benchmark."""
from types import SimpleNamespace

import pytest

from validation import paired_voice as paired


def _page(title="Velinimet", paragraphs=None):
    paragraphs = paragraphs or ["Bir yazar burada kısa bir metin anlattı. " * 80]
    return (
        f'<html><h1 id="firstHeading">{title}</h1>'
        '<div id="mw-content-text"><div class="mw-parser-output">'
        '<table><tr><td>Site navigation should be discarded</td></tr></table>'
        + "".join(f"<p>{p}</p>" for p in paragraphs)
        + "</div></div></html>"
    )


def test_wikisource_extract_rejects_wrong_work_and_short_body():
    with pytest.raises(ValueError, match="Unexpected Wikisource"):
        paired._wikisource_text(_page(title="A different work"), "Velinimet")
    with pytest.raises(ValueError, match="Too little"):
        paired._wikisource_text(_page(paragraphs=["Az kelime."]), "Velinimet")
    result = paired._wikisource_text(_page(), "Velinimet")
    assert "navigation" not in result
    assert len(result.split()) >= 350


def test_excerpt_requires_substantial_independent_source_text():
    with pytest.raises(ValueError, match="short"):
        paired._excerpt("a b c", 4)
    assert paired._excerpt("first second third fourth", 3) == "first second third"


def test_long_span_copy_detection_and_distances():
    source = ("First we looked across the crowded square and noticed nothing "
              "until the heavy bells started to ring loudly outside. " * 20)
    assert paired.copied_long_span(source, (source,))
    assert not paired.copied_long_span("Completely different words.", (source,))
    assert paired.heldout_distance(source, source, "en") == 0
    assert 0 <= paired.heldout_distance("A very different thing happened.", source, "en") <= 1


def test_pair_comparison_has_length_and_language_disclosures():
    sample = ("Ben bugün kısa bir hikâye anlatıyorum. "
              "Ama bu yalnızca kurmaca bir olay. ") * 40
    case = paired.Case("fixture-tr", "Fixture", "tr", (sample,), sample, ())
    result = paired.evaluate_pair(sample, sample, case)
    assert result["length_comparable"]
    assert result["styled_language"] == "tr"
    assert result["styled_heldout_distance"] == result["neutral_heldout_distance"]
    assert not result["eligible_for_style_comparison"]
    assert "severe_text_repetition" in result["invalid_reasons"]
    assert result["styled_better_on_descriptive_distance"] is None
    result = paired.evaluate_pair(sample, "Tek kelime.", case)
    assert not result["length_comparable"]
    assert "incomparable_lengths" in result["invalid_reasons"]
    assert "insufficient_output_length" in result["invalid_reasons"]
    assert result["styled_better_on_descriptive_distance"] is None



def test_wrong_language_is_ineligible_even_if_distance_is_better():
    tr = " ".join(
        f"Bugün burada {chr(97 + i)} kararı verdim ve sonra dinlendim."
        for i in range(23)
    )
    en = " ".join(
        f"The traveler explored region {chr(97 + i)} and returned after sunset."
        for i in range(23)
    )
    case = paired.Case("case-tr", "Writer", "tr", (tr,), tr, ())
    result = paired.evaluate_pair(en, tr, case)
    assert result["styled_language"] == "en"
    assert not result["eligible_for_style_comparison"]
    assert "unverified_output_language" in result["invalid_reasons"]
    assert result["styled_better_on_descriptive_distance"] is None


def test_eligible_pair_can_have_a_real_comparison_without_assumed_superiority():
    heldout = " ".join(
        f"The {chr(97 + i)} traveler considered {chr(97 + i)} options "
        f"before {chr(97 + i)} crossings as the evening approached."
        for i in range(23)
    )
    case = paired.Case("case-en", "Writer", "en",
                       ("This training passage has a different structure.",),
                       heldout, ())
    controlled = paired.evaluate_pair(heldout, heldout + " Extra detail.", case)
    assert controlled["eligible_for_style_comparison"]
    assert controlled["styled_better_on_descriptive_distance"] is True
    assert controlled["invalid_reasons"] == []


def test_fixed_source_allowlist_rejects_unapproved_url_without_network(monkeypatch):
    monkeypatch.setattr(paired.requests, "get", lambda *args, **kwargs: pytest.fail("network"))
    with pytest.raises(ValueError, match="Unapproved"):
        paired._fixed_source("https://example.org/secret")


def test_neutral_model_run_is_local_and_proxy_free(monkeypatch):
    class MockSession:
        trust_env = True

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def post(self, url, **kwargs):
            assert not self.trust_env
            assert url == "http://127.0.0.1:11434/api/chat"
            assert kwargs["json"]["model"] == paired.MODEL
            assert kwargs["json"]["stream"] is False
            assert kwargs["json"]["options"] == {"num_predict": paired.MAX_TOKENS}
            return SimpleNamespace(
                raise_for_status=lambda: None,
                json=lambda: {"message": {"content": "A complete neutral draft."}},
            )

    monkeypatch.setattr(paired.requests, "Session", MockSession)
    assert paired._neutral("An original scene.", "en") == "A complete neutral draft."


def test_incomplete_generation_is_ineligible_even_if_style_distance_looks_better():
    heldout = " ".join(
        f"The {chr(97 + i)} traveler considered {chr(97 + i)} options "
        f"before {chr(97 + i)} crossings as the evening approached."
        for i in range(23)
    )
    case = paired.Case("case-en", "Writer", "en", ("Source paragraph.",), heldout, ())
    result = paired.evaluate_pair(
        heldout, heldout + " Extra detail.", case,
        styled_completion="truncated", neutral_completion="unknown",
    )
    assert result["styled_completion_status"] == "truncated"
    assert result["neutral_completion_status"] == "unknown"
    assert "styled_generation_truncated" in result["invalid_reasons"]
    assert "neutral_generation_unknown" in result["invalid_reasons"]
    assert not result["eligible_for_style_comparison"]
    assert result["styled_better_on_descriptive_distance"] is None


def test_neutral_optional_receipt_exposes_model_length_cutoff(monkeypatch):
    class Session:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def post(self, url, **kwargs):
            assert not self.trust_env
            return SimpleNamespace(
                raise_for_status=lambda: None,
                json=lambda: {
                    "message": {"content": "A usable but unfinished text"},
                    "done": True,
                    "done_reason": "length",
                    "eval_count": paired.MAX_TOKENS,
                },
            )

    monkeypatch.setattr(paired.requests, "Session", Session)
    receipt = paired._neutral("A fictional scene.", "en", return_metadata=True)
    assert receipt.text == "A usable but unfinished text"
    assert receipt.completion_status == "truncated"
    assert receipt.generated_tokens == paired.MAX_TOKENS
    assert paired._neutral("A fictional scene.", "en") == receipt.text

    # Paired model comparisons must use a shared, explicit seed.
    def seeded_session():
        class Session:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def post(self, url, **kwargs):
                assert kwargs["json"]["options"] == {
                    "num_predict": paired.MAX_TOKENS, "seed": 315
                }
                return SimpleNamespace(
                    raise_for_status=lambda: None,
                    json=lambda: {"message": {"content": "Seeded output."},
                                  "done": True, "done_reason": "stop"},
                )
        return Session()

    monkeypatch.setattr(paired.requests, "Session", seeded_session)
    assert paired._neutral("A scene.", "en", seed=315) == "Seeded output."

