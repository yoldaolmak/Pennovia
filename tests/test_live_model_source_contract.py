"""Offline guardrails for the external, real-model validation script."""
import pytest

from validation.live_model import select_chapters


def _fake_book() -> str:
    headings = ("I", "II", "III", "IV", "V")
    parts = ["The Innocents Abroad\nMark Twain\n\n"
             "   CHAPTER I.\nThis is the table of contents, not body text.\n"
             "\n    PREFACE\n\nNarrative preface.\n"]
    for chapter in headings:
        parts.append(f"\nCHAPTER {chapter}.\n\n")
        parts.append(("This is independent chapter content with meaningful prose. "
                      + chapter + " ") * 45)
        parts.append("\n\n")
    return "".join(parts)


def test_training_and_holdout_segments_do_not_overlap():
    chunks = select_chapters(_fake_book())
    assert set(chunks) == {"I", "II", "III", "IV"}
    assert all(len(chunk.split()) >= 350 for chunk in chunks.values())
    assert all(chunks[key] != chunks["III"] for key in ("I", "II", "IV"))


def test_source_requires_expected_work_and_one_real_heading_per_chapter():
    with pytest.raises(ValueError, match="Mark Twain"):
        select_chapters(_fake_book().replace("Mark Twain", "Unknown"))
    with pytest.raises(ValueError, match="Missing body heading III"):
        select_chapters(_fake_book().replace("\nCHAPTER III.\n", "\nUNKNOWN CHAPTER\n"))


def test_missing_or_short_chapter_fails_closed():
    book = _fake_book().replace(
        ("This is independent chapter content with meaningful prose. II ") * 45,
        "Just a sentence.",
    )
    with pytest.raises(ValueError, match="unexpectedly short"):
        select_chapters(book)

def test_crlf_normalization_matches_gutenberg_download_format():
    raw = _fake_book().replace("\n", "\r\n").encode("utf-8")
    decoded = raw.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    assert len(select_chapters(decoded)) == 4


def test_gutenberg_mirror_fallback_is_source_verified_and_attributed(monkeypatch):
    import hashlib
    import requests

    from validation import live_model

    book = _fake_book().encode("utf-8")
    urls = []

    class Response:
        content = book

        def raise_for_status(self):
            pass

    def fake_get(url, **kwargs):
        urls.append(url)
        if url == live_model.SOURCE:
            raise requests.HTTPError("Synthetic Gutenberg 503")
        return Response()

    monkeypatch.setattr(live_model.requests, "get", fake_get)
    text, digest, source = live_model._download_source()
    assert source == live_model.MIRROR
    assert digest == hashlib.sha256(book).hexdigest()
    assert text == book.decode("utf-8")
    assert urls == [live_model.SOURCE, live_model.MIRROR]
    assert set(live_model.select_chapters(text)) == {"I", "II", "III", "IV"}



def test_bounded_real_model_control_uses_direct_loopback_and_token_limit(monkeypatch):
    from types import SimpleNamespace
    from validation import live_model

    class Session:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def post(self, url, **kwargs):
            assert self.trust_env is False
            assert url == live_model.OLLAMA + "/api/chat"
            assert kwargs["json"]["model"] == live_model.MODEL
            assert kwargs["json"]["options"] == {
                "num_predict": live_model.MAX_PREDICT_TOKENS
            }
            assert kwargs["json"]["stream"] is False
            return SimpleNamespace(
                raise_for_status=lambda: None,
                json=lambda: {"message": {"content": "A neutral sentence. " * 55}},
            )

    monkeypatch.setattr(live_model.requests, "Session", Session)
    assert len(live_model._baseline("A topic").split()) >= 50
    assert 64 <= live_model.MAX_PREDICT_TOKENS <= 8192
