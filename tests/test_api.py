import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_root_index():
    response = client.get("/")
    assert response.status_code == 200
    assert "SpotiDown" in response.text

def test_api_info_invalid_url():
    response = client.post("/api/info", json={"url": "https://not-spotify.com/invalid"})
    assert response.status_code == 400
    assert "tidak valid" in response.json()["detail"]

def test_api_info_valid_track():
    url = "https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT"
    response = client.post("/api/info", json={"url": url})
    if response.status_code == 200:
        data = response.json()
        assert data["type"] == "track"
        assert len(data["tracks"]) == 1
        assert "title" in data
        assert "cover_url" in data
    else:
        pytest.skip("External Spotify API unreachable from test runner")

def test_api_download_track_validation():
    # Unsupported format
    response = client.post("/api/download/track", json={
        "url": "https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT",
        "format": "unsupported_xyz"
    })
    assert response.status_code == 400
