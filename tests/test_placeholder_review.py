"""An uncalibrated voice score must not approve unfinished release content."""

from pennovia.audit import audit
from pennovia.studio.server import _review
from pennovia.voice.analyzer import analyze


SAMPLE = ("I walked past the old market in the rain. "
          "The road was empty, but I wanted to continue. ") * 24


def test_high_score_with_real_placeholders_fails_editorial_audit():
    profile = analyze([SAMPLE], language="en")
    clean = audit(SAMPLE, profile)
    assert clean.total_score >= 70
    assert clean.passed()

    draft = SAMPLE + "\n\n" + (
        "Take a taxi from [Bus Station Name] to ____, where a ticket "
        "costs [Taxi Fare]. The walk takes approximately [Distance]."
    )
    result = audit(draft, profile)
    assert result.total_score >= 70
    assert not result.passed()
    assert "unresolved_placeholder" in result.issues
    assert result.details["unresolved_placeholders"] >= 3
    assert "[FAIL]" in result.report()
    studio = _review(draft, profile)
    assert studio["passed"] is False
    assert "unresolved_placeholder" in studio["issues"]


def test_references_links_and_markdown_rules_are_not_placeholders():
    profile = analyze([SAMPLE], language="en")
    draft = SAMPLE + "\n\n" + (
        "See reference [1] or [the official guide](https://example.org).\n\n___"
    )
    result = audit(draft, profile)
    assert "unresolved_placeholder" not in result.issues
    assert result.details["unresolved_placeholders"] == 0
