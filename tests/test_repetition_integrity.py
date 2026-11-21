"""Strong, cross-language repetition loops cannot masquerade as voice fidelity."""
from pennovia.audit import audit
from pennovia.studio.server import _review
from pennovia.voice.analyzer import VoiceProfile
from pennovia.voice.integrity import repeated_fourgram_share


def _profile() -> VoiceProfile:
    return VoiceProfile(
        language="en", avg_sentence_words=15, avg_paragraph_sentences=1.0,
        vocabulary_richness=0.71,
    )


def test_severe_repeated_prose_fails_even_when_style_heuristic_is_high():
    phrase = (
        "Every day the traveler went to the market and returned "
        "without a sensible plan."
    )
    draft = "\n\n".join([phrase] * 24)
    profile = _profile()
    raw = audit(draft, profile)
    assert raw.total_score >= 70
    assert "severe_text_repetition" in raw.issues
    assert raw.details["repeated_fourgram_share"] >= 0.45
    assert raw.details["max_fourgram_occurrences"] >= 20
    assert not raw.passed()
    assert "[FAIL]" in raw.report()
    studio = _review(draft, profile)
    assert not studio["passed"]
    assert "severe_text_repetition" in studio["issues"]


def test_diverse_prose_does_not_trigger_repetition_gate():
    # Fresh words in each paragraph keep the four-gram overlap minimal.
    repeated_intro = "Every day the traveler walked a familiar street."
    text = "\n\n".join(
        repeated_intro + " " + " ".join(
            f"site{chr(97 + i)}{chr(97 + j)}description" for j in range(14)
        ) for i in range(22)
    )
    share, _, tokens = repeated_fourgram_share(text)
    assert tokens >= 120
    assert share >= 0.15  # deliberate repeating lead-in merits a warning
    result = audit(text, _profile())
    assert "formulaic_repetition_warning" in result.issues
    assert "severe_text_repetition" not in result.issues


def test_genuinely_distinct_phrases_have_low_repeat_share():
    text = " ".join(
        " ".join(f"detail{chr(97 + i)}{chr(97 + j)}remark"
                 for j in range(12))
        for i in range(22)
    )
    # Fixed function words will recur, but do not account for half the four-grams.
    share, _, total = repeated_fourgram_share(text)
    assert total >= 120
    assert share < 0.45


def test_short_sample_never_receives_blocking_repeat_flag():
    text = "Nothing more was said. " * 9
    result = audit(text, _profile())
    assert "severe_text_repetition" not in result.issues
    assert "too_short" in result.issues


def test_style_imitation_from_repetitive_author_does_not_claim_degeneration():
    # An author's explicitly repetitive source style is not enough to
    # certify human-like prose or mandate a content ban.
    profile = _profile()
    profile.vocabulary_richness = 0.04
    draft = "\n\n".join(["I walked the road and then I walked the road again."] * 30)
    result = audit(draft, profile)
    assert result.details["repeated_fourgram_share"] >= 0.45
    assert "severe_text_repetition" not in result.issues
