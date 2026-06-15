import os
import json
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import pytest


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_storage_env(monkeypatch):
    monkeypatch.setenv("R2_ENDPOINT_URL", "https://fake.r2.example.com")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "key")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setenv("R2_BUCKET_NAME", "testbucket")


# ── is_configured ─────────────────────────────────────────────────────────────

def test_is_configured_true(monkeypatch):
    _make_storage_env(monkeypatch)
    import importlib
    import storage
    importlib.reload(storage)
    assert storage.is_configured() is True


def test_is_configured_false_when_env_missing():
    for var in ("R2_ENDPOINT_URL", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME"):
        os.environ.pop(var, None)
    import importlib
    import storage
    importlib.reload(storage)
    assert storage.is_configured() is False


# ── sync_templates_from_r2 ───────────────────────────────────────────────────

def test_sync_templates_downloads_missing_file(tmp_path, monkeypatch):
    _make_storage_env(monkeypatch)
    import importlib
    import storage
    importlib.reload(storage)

    fake_client = MagicMock()
    fake_client.list_objects_v2.return_value = {
        "Contents": [{"Key": "templates/my-template.json", "LastModified": MagicMock()}]
    }

    with patch.object(storage, "_client", fake_client):
        storage.sync_templates_from_r2(tmp_path)

    fake_client.download_file.assert_called_once_with(
        "testbucket", "templates/my-template.json", str(tmp_path / "my-template.json")
    )


def test_sync_templates_noop_when_not_configured(tmp_path, monkeypatch):
    for var in ("R2_ENDPOINT_URL", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME"):
        monkeypatch.delenv(var, raising=False)
    import importlib
    import storage
    importlib.reload(storage)

    # Should not raise and should not touch tmp_path
    storage.sync_templates_from_r2(tmp_path)
    assert list(tmp_path.iterdir()) == []


# ── push_template ─────────────────────────────────────────────────────────────

def test_push_template_uploads_file(tmp_path, monkeypatch):
    _make_storage_env(monkeypatch)
    import importlib
    import storage
    importlib.reload(storage)

    tpl = tmp_path / "my-template.json"
    tpl.write_text(json.dumps({"name": "my-template"}))

    fake_client = MagicMock()
    with patch.object(storage, "_client", fake_client):
        storage.push_template(tpl, tmp_path)

    fake_client.upload_file.assert_called_once_with(
        str(tpl), "testbucket", "templates/my-template.json"
    )


def test_push_template_noop_when_not_configured(tmp_path, monkeypatch):
    for var in ("R2_ENDPOINT_URL", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME"):
        monkeypatch.delenv(var, raising=False)
    import importlib
    import storage
    importlib.reload(storage)

    tpl = tmp_path / "x.json"
    tpl.write_text("{}")
    storage.push_template(tpl, tmp_path)  # must not raise


# ── delete_template ───────────────────────────────────────────────────────────

def test_delete_template_calls_delete_object(monkeypatch):
    _make_storage_env(monkeypatch)
    import importlib
    import storage
    importlib.reload(storage)

    fake_client = MagicMock()
    with patch.object(storage, "_client", fake_client):
        storage.delete_template("templates/my-template.json")

    fake_client.delete_object.assert_called_once_with(
        Bucket="testbucket", Key="templates/my-template.json"
    )


# ── upload_export ─────────────────────────────────────────────────────────────

def test_upload_export_returns_presigned_url(tmp_path, monkeypatch):
    _make_storage_env(monkeypatch)
    import importlib
    import storage
    importlib.reload(storage)

    export_file = tmp_path / "output.mp4"
    export_file.write_bytes(b"fake video")

    fake_client = MagicMock()
    fake_client.generate_presigned_url.return_value = "https://r2.example.com/presigned"

    with patch.object(storage, "_client", fake_client):
        url = storage.upload_export(export_file)

    assert url == "https://r2.example.com/presigned"
    fake_client.upload_file.assert_called_once_with(
        str(export_file), "testbucket", f"exports/{export_file.name}"
    )
    assert not export_file.exists()  # local file deleted after upload


def test_upload_export_returns_none_when_not_configured(tmp_path, monkeypatch):
    for var in ("R2_ENDPOINT_URL", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME"):
        monkeypatch.delenv(var, raising=False)
    import importlib
    import storage
    importlib.reload(storage)

    export_file = tmp_path / "output.mp4"
    export_file.write_bytes(b"fake video")

    result = storage.upload_export(export_file)
    assert result is None
    assert export_file.exists()  # not deleted when R2 unconfigured
