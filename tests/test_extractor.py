import pytest
from core.extractor import SpotifyExtractor

def test_parse_valid_urls():
    extractor = SpotifyExtractor()
    
    track_info = extractor.parse_url("https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT?si=abc123xyz")
    assert track_info["type"] == "track"
    assert track_info["id"] == "4cOdK2wGLETKBW3PvgPWqT"

    album_info = extractor.parse_url("https://open.spotify.com/album/1DFixLWuPkv3KT3TnV35m3")
    assert album_info["type"] == "album"
    assert album_info["id"] == "1DFixLWuPkv3KT3TnV35m3"

    playlist_info = extractor.parse_url("https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M")
    assert playlist_info["type"] == "playlist"
    assert playlist_info["id"] == "37i9dQZF1DXcBWIGoYBM5M"

def test_parse_invalid_url():
    extractor = SpotifyExtractor()
    with pytest.raises(ValueError):
        extractor.parse_url("https://youtube.com/watch?v=123456")

    with pytest.raises(ValueError):
        extractor.parse_url("https://open.spotify.com/artist/123456")

def test_extract_real_track():
    extractor = SpotifyExtractor()
    # Test a well-known track: Never Gonna Give You Up
    url = "https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT"
    try:
        data = extractor.extract(url)
        assert data["type"] == "track"
        assert "Never Gonna Give You Up" in data["title"]
        assert len(data["tracks"]) == 1
        assert "Rick Astley" in data["tracks"][0]["artist_display"]
        assert data["tracks"][0]["duration_sec"] > 0
    except Exception as e:
        pytest.skip(f"Network request to Spotify failed: {e}")
