import io, pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c

def test_upload_audio_missing_file(client):
    resp = client.post('/api/upload-audio')
    assert resp.status_code == 400
    assert b'file' in resp.data

def test_upload_audio_wrong_extension(client):
    data = {'file': (io.BytesIO(b'fake'), 'track.exe')}
    resp = client.post('/api/upload-audio', data=data, content_type='multipart/form-data')
    assert resp.status_code == 400
    assert b'extension' in resp.data.lower()

def test_upload_audio_success(client, tmp_path, monkeypatch):
    import app as app_module
    monkeypatch.setattr(app_module, 'UPLOADS_DIR', tmp_path)
    data = {'file': (io.BytesIO(b'\xff\xfb\x90\x00'), 'song.mp3')}
    resp = client.post('/api/upload-audio', data=data, content_type='multipart/form-data')
    assert resp.status_code == 200
    body = resp.get_json()
    assert 'path' in body
    assert body['path'].startswith('uploads/')
    assert body['path'].endswith('.mp3')
    saved_files = list(tmp_path.iterdir())
    assert len(saved_files) == 1
    assert saved_files[0].suffix == '.mp3'
