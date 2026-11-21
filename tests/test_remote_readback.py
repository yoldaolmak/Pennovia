"""Remote verification requires a real authenticated readback, never POST alone.

All cases are synthetic and must not touch an actual WordPress or Drive site.
"""
import json
import sys
from types import ModuleType, SimpleNamespace

import pytest
import requests

from pennovia.exporter import writer


def _wp_response(status, data):
    return SimpleNamespace(
        status_code=status, json=lambda: data,
        raise_for_status=lambda: None,
    )


@pytest.mark.parametrize("status", ["draft", "publish"])
def test_wordpress_optional_readback_verifies_id_content_status_and_auth(monkeypatch, status):
    posts = []
    gets = []

    def post(url, **kwargs):
        posts.append((url, kwargs))
        return _wp_response(201, {"id": 42, "link": "https://wp.example.org/?p=42"})

    def get(url, **kwargs):
        gets.append((url, kwargs))
        return _wp_response(200, {
            "id": 42, "status": status,
            "content": {"raw": writer._html_body("A complete fictional draft.")},
        })

    monkeypatch.setattr(requests, "post", post)
    monkeypatch.setattr(requests, "get", get)
    output = writer.save_wordpress(
        "A complete fictional draft.", "Title",
        wp_url="https://wp.example.org", wp_user="writer", wp_password="secret",
        publish=(status == "publish"), verify_readback=True,
    )
    assert output == "https://wp.example.org/?p=42"
    assert len(posts) == len(gets) == 1
    assert posts[0][1]["json"]["status"] == status
    assert gets[0][0] == "https://wp.example.org/wp-json/wp/v2/posts/42?context=edit"
    assert gets[0][1]["auth"] == ("writer", "secret")
    assert gets[0][1]["verify"] is True
    assert gets[0][1]["allow_redirects"] is False


@pytest.mark.parametrize("response,expected", [
    ({"id": 42, "status": "publish", "content": {"raw": writer._html_body("Draft")}}, "does not match"),
    ({"id": 43, "status": "draft", "content": {"raw": writer._html_body("Draft")}}, "does not match"),
    ({"id": 42, "status": "draft", "content": {"raw": "changed remotely"}}, "does not match"),
    ({}, "does not match"),
])
def test_wordpress_readback_mismatch_never_claims_remote_success(monkeypatch, response, expected):
    monkeypatch.setattr(requests, "post", lambda *a, **k: _wp_response(
        201, {"id": 42, "link": "https://wp.example.org/draft"}
    ))
    monkeypatch.setattr(requests, "get", lambda *a, **k: _wp_response(200, response))
    with pytest.raises(writer.RemoteOutcomeUnknown, match=expected):
        writer.save_wordpress(
            "Draft", "Title", wp_url="https://wp.example.org",
            wp_user="writer", wp_password="secret", verify_readback=True,
        )


@pytest.mark.parametrize("response", [
    {"link": "https://wp.example.org/draft"},
    {"id": True, "link": "https://wp.example.org/draft"},
    {"id": 0, "link": "https://wp.example.org/draft"},
])
def test_wordpress_readback_requires_real_post_id(monkeypatch, response):
    monkeypatch.setattr(requests, "post", lambda *a, **k: _wp_response(201, response))
    monkeypatch.setattr(requests, "get", lambda *a, **k: pytest.fail("must not GET"))
    with pytest.raises(writer.RemoteOutcomeUnknown, match="valid post ID"):
        writer.save_wordpress(
            "Draft", "Title", wp_url="https://wp.example.org",
            wp_user="writer", wp_password="secret", verify_readback=True,
        )


def test_wordpress_readback_timeout_is_outcome_unknown_not_retryable(monkeypatch):
    post_count = []

    def post(*args, **kwargs):
        post_count.append(1)
        return _wp_response(201, {"id": 42, "link": "https://wp.example.org/draft"})

    monkeypatch.setattr(requests, "post", post)
    monkeypatch.setattr(requests, "get", lambda *a, **k: (
        _ for _ in ()
    ).throw(requests.ReadTimeout("secret-no-readback")))
    with pytest.raises(writer.RemoteOutcomeUnknown, match="uncertain") as err:
        writer.save_wordpress(
            "Draft", "Title", wp_url="https://wp.example.org",
            wp_user="writer", wp_password="secret", verify_readback=True,
        )
    assert len(post_count) == 1
    assert "secret-no-readback" not in str(err.value)


def _drive(monkeypatch, *, change=None, get_error=None, upload=None):
    """Install deterministic fake Google API, including content readback."""
    google = ModuleType("google")
    google.__path__ = []
    oauth2 = ModuleType("google.oauth2")
    oauth2.__path__ = []
    credentials = ModuleType("google.oauth2.credentials")
    api = ModuleType("googleapiclient")
    api.__path__ = []
    discovery = ModuleType("googleapiclient.discovery")
    http = ModuleType("googleapiclient.http")
    created = []
    observed = []

    class Credentials:
        @staticmethod
        def from_authorized_user_info(info):
            assert info == {"token": "synthetic"}
            return object()

    class Upload:
        def __init__(self, data, mimetype):
            observed.append((data, mimetype))

    class Request:
        def __init__(self, kind):
            self.kind = kind

        def execute(self):
            if self.kind == "create":
                return {"id": "file1", "webViewLink": "https://drive.example/view"}
                if upload is None else upload
            if get_error:
                raise get_error
            if self.kind == "get":
                details = {
                    "id": "file1", "name": created[0]["body"]["name"],
                    "mimeType": "text/plain",
                }
                if change == "name":
                    details["name"] = "wrong.txt"
                if change == "id":
                    details["id"] = "file2"
                return details
            if self.kind == "get_media":
                return b"wrong file" if change == "bytes" else observed[0][0]
            raise AssertionError("Unexpected fake Drive call")

    class Service:
        def files(self):
            return self

        def create(self, **kwargs):
            created.append(kwargs)
            return Request("create")

        def get(self, **kwargs):
            assert kwargs["fileId"] == "file1"
            assert kwargs["fields"] == "id,name,mimeType"
            return Request("get")

        def get_media(self, **kwargs):
            assert kwargs["fileId"] == "file1"
            return Request("get_media")

    credentials.Credentials = Credentials
    discovery.build = lambda *a, **kw: Service()
    http.MediaInMemoryUpload = Upload
    for name, module in {
        "google": google,
        "google.oauth2": oauth2,
        "google.oauth2.credentials": credentials,
        "googleapiclient": api,
        "googleapiclient.discovery": discovery,
        "googleapiclient.http": http,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)
    monkeypatch.setenv("GOOGLE_DRIVE_TOKEN", json.dumps({"token": "synthetic"}))
    return created, observed


def test_drive_optional_readback_checks_remote_id_name_mime_and_bytes(monkeypatch):
    created, observed = _drive(monkeypatch)
    link = writer.save_google_drive(
        "Exactly one editable paragraph.", "Travel note", "txt",
        verify_readback=True,
    )
    assert link == "https://drive.example/view"
    assert len(created) == 1
    assert observed == [(b"Exactly one editable paragraph.", "text/plain")]


@pytest.mark.parametrize("change", ["name", "id", "bytes"])
def test_drive_readback_mismatch_never_confirms_upload(monkeypatch, change):
    _drive(monkeypatch, change=change)
    with pytest.raises(writer.RemoteOutcomeUnknown, match="differs"):
        writer.save_google_drive("Actual bytes", "Title", "txt", verify_readback=True)


def test_drive_readback_error_never_causes_implicit_second_upload(monkeypatch):
    created, _ = _drive(monkeypatch, get_error=RuntimeError("secret fail"))
    with pytest.raises(writer.RemoteOutcomeUnknown, match="uncertain") as err:
        writer.save_google_drive("Draft", "Title", "txt", verify_readback=True)
    assert len(created) == 1
    assert "secret fail" not in str(err.value)


def test_verification_is_opt_in_and_boolean(monkeypatch):
    with pytest.raises(ValueError, match="verify_readback"):
        writer.save_google_drive("Draft", "Title", "txt", verify_readback="yes")
    with pytest.raises(ValueError, match="verify_readback"):
        writer.save_wordpress("Draft", "Title", verify_readback=1)
