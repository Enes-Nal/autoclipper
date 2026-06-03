import io, json, pytest
from pathlib import Path
from app import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    import app as app_module
    sfx_dir = tmp_path / "sfx"
    sfx_dir.mkdir()
    lib_path = tmp_path / "sfx_library.json"
    monkeypatch.setattr(app_module, "SFX_DIR", sfx_dir)
    monkeypatch.setattr(app_module, "SFX_LIB_PATH", lib_path)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_list_sfx_empty(client):
    resp = client.get("/api/sfx")
    assert resp.status_code == 200
    assert resp.get_json() == {"sounds": []}


def test_upload_sfx_success(client):
    data = {"file": (io.BytesIO(b"\xff\xfb\x90\x00"), "boom.mp3")}
    resp = client.post("/api/sfx/upload", data=data,
                       content_type="multipart/form-data")
    assert resp.status_code == 200
    body = resp.get_json()
    assert "id" in body
    assert body["name"] == "boom"
    assert body["path"].startswith("sfx/")
    # appears in list
    list_resp = client.get("/api/sfx")
    sounds = list_resp.get_json()["sounds"]
    assert len(sounds) == 1
    assert sounds[0]["id"] == body["id"]


def test_upload_sfx_wrong_extension(client):
    data = {"file": (io.BytesIO(b"data"), "sound.exe")}
    resp = client.post("/api/sfx/upload", data=data,
                       content_type="multipart/form-data")
    assert resp.status_code == 400
    assert b"extension" in resp.data.lower()


def test_upload_sfx_missing_file(client):
    resp = client.post("/api/sfx/upload")
    assert resp.status_code == 400


def test_rename_sfx(client):
    # upload first
    data = {"file": (io.BytesIO(b"\xff\xfb\x90\x00"), "snap.mp3")}
    up = client.post("/api/sfx/upload", data=data,
                     content_type="multipart/form-data")
    sfx_id = up.get_json()["id"]
    # rename
    resp = client.patch(f"/api/sfx/{sfx_id}/rename",
                        json={"name": "Snap Effect"})
    assert resp.status_code == 200
    sounds = client.get("/api/sfx").get_json()["sounds"]
    assert sounds[0]["name"] == "Snap Effect"


def test_rename_sfx_not_found(client):
    resp = client.patch("/api/sfx/nonexistent/rename",
                        json={"name": "X"})
    assert resp.status_code == 404


def test_rename_sfx_empty_name(client):
    data = {"file": (io.BytesIO(b"\xff\xfb\x90\x00"), "snap.mp3")}
    up = client.post("/api/sfx/upload", data=data,
                     content_type="multipart/form-data")
    sfx_id = up.get_json()["id"]
    resp = client.patch(f"/api/sfx/{sfx_id}/rename", json={"name": ""})
    assert resp.status_code == 400


def test_delete_sfx(client):
    data = {"file": (io.BytesIO(b"\xff\xfb\x90\x00"), "click.mp3")}
    up = client.post("/api/sfx/upload", data=data,
                     content_type="multipart/form-data")
    sfx_id = up.get_json()["id"]
    resp = client.delete(f"/api/sfx/{sfx_id}")
    assert resp.status_code == 200
    sounds = client.get("/api/sfx").get_json()["sounds"]
    assert sounds == []


def test_delete_sfx_not_found(client):
    resp = client.delete("/api/sfx/nonexistent")
    assert resp.status_code == 404


def test_serve_sfx_file(client):
    data = {"file": (io.BytesIO(b"\xff\xfb\x90\x00"), "test.mp3")}
    up = client.post("/api/sfx/upload", data=data,
                     content_type="multipart/form-data")
    path = up.get_json()["path"]   # e.g. "sfx/abc123.mp3"
    filename = path.split("/")[-1]
    resp = client.get(f"/api/sfx/files/{filename}")
    assert resp.status_code == 200
