import requests

import supabase_storage
from supabase_storage import BUCKET, upload_export_file


class FakeResponse:
    def __init__(self, status_code, text=""):
        self.status_code = status_code
        self.text = text


def test_returns_the_storage_path_on_success(monkeypatch):
    calls = []

    def fake_post(url, headers=None, data=None, timeout=None):
        calls.append({"url": url, "headers": headers, "data": data})
        return FakeResponse(200)

    monkeypatch.setattr(supabase_storage.requests, "post", fake_post)
    result = upload_export_file(b"csv,bytes", "abc123", "https://example.supabase.co", "service-key")

    assert result == "exports/abc123.csv"
    assert calls[0]["url"] == f"https://example.supabase.co/storage/v1/object/{BUCKET}/exports/abc123.csv"
    assert calls[0]["headers"]["Authorization"] == "Bearer service-key"
    assert calls[0]["headers"]["apikey"] == "service-key"
    assert calls[0]["data"] == b"csv,bytes"


def test_returns_none_on_non_success_status_without_raising(monkeypatch):
    monkeypatch.setattr(supabase_storage.requests, "post", lambda *a, **k: FakeResponse(403, "Forbidden"))
    result = upload_export_file(b"csv,bytes", "abc123", "https://example.supabase.co", "bad-key")
    assert result is None


def test_returns_none_on_network_failure_without_raising(monkeypatch):
    def raise_connection_error(*args, **kwargs):
        raise requests.ConnectionError("boom")

    monkeypatch.setattr(supabase_storage.requests, "post", raise_connection_error)
    result = upload_export_file(b"csv,bytes", "abc123", "https://example.supabase.co", "service-key")
    assert result is None


def test_returns_none_on_timeout_without_raising(monkeypatch):
    def raise_timeout(*args, **kwargs):
        raise requests.Timeout("too slow")

    monkeypatch.setattr(supabase_storage.requests, "post", raise_timeout)
    result = upload_export_file(b"csv,bytes", "abc123", "https://example.supabase.co", "service-key")
    assert result is None
