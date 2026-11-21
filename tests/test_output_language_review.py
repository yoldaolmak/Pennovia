"""A recognisably wrong output language cannot pass voice review."""
from pennovia.audit import audit
from pennovia.studio.server import _review
from pennovia.voice.analyzer import analyze


TR = (
    "Ben bugün burada uzun süre kaldım. Ama sonra bir karara vardım. "
    "Siz bu yolu nasıl görüyorsunuz? Biz daha sonra birlikte gideriz. "
) * 25
EN = (
    "I walked through the town and saw a small shop. "
    "The street was quiet but the people were still working. "
    "We could see the river from the narrow old bridge. "
) * 25


def test_explicit_turkish_profile_rejects_long_english_draft():
    profile = analyze([TR], language="tr")
    result = audit(EN, profile)
    assert result.details["observed_language"] == "en"
    assert "output_language_mismatch" in result.issues
    assert not result.passed()
    assert "[FAIL]" in result.report()
    studio = _review(EN, profile)
    assert studio["passed"] is False
    assert "output_language_mismatch" in studio["issues"]


def test_explicit_english_profile_rejects_long_turkish_draft():
    result = audit(TR, analyze([EN], language="en"))
    assert result.details["observed_language"] == "tr"
    assert "output_language_mismatch" in result.issues
    assert not result.passed()


def test_correct_language_and_unknown_evidence_do_not_fail_closed():
    tr = audit(TR, analyze([TR], language="tr"))
    assert tr.passed()
    assert tr.details["observed_language"] == "tr"
    assert "output_language_mismatch" not in tr.issues

    # An ambiguous answer should not be called English purely because the
    # profile is Turkish: the review remains uncertain, not deceptively sure.
    ambiguous = audit(("Kapadokya İstanbul Ankara. " * 90), analyze([TR], language="tr"))
    assert ambiguous.details["observed_language"] == "auto"
    assert "output_language_mismatch" not in ambiguous.issues


def test_unknown_profile_language_does_not_force_draft_language():
    profile = analyze([TR], language="tr")
    profile.language = "auto"
    result = audit(EN, profile)
    assert result.details["observed_language"] == "en"
    assert "output_language_mismatch" not in result.issues
