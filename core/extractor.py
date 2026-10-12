import re
import json
import logging
from typing import Dict, Any, List, Optional
import requests

logger = logging.getLogger(__name__)

SPOTIFY_URL_PATTERN = re.compile(
    r"https?://open\.spotify\.com/(?P<type>track|album|playlist)/(?P<id>[a-zA-Z0-9]+)"
)

class SpotifyExtractor:
    """Zero-auth Spotify metadata extractor."""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        })
        self._access_token: Optional[str] = None

    def parse_url(self, url: str) -> Dict[str, str]:
        """Validate and extract item type and ID from Spotify URL."""
        match = SPOTIFY_URL_PATTERN.search(url)
        if not match:
            raise ValueError("URL Spotify tidak valid. Gunakan format track, album, atau playlist Spotify.")
        return {"type": match.group("type"), "id": match.group("id")}

    def _get_anonymous_token(self) -> Optional[str]:
        """Fetch Spotify anonymous web player access token."""
        try:
            resp = self.session.get(
                "https://open.spotify.com/get_access_token?reason=transport&productType=web_player",
                timeout=self.timeout
            )
            if resp.status_code == 200:
                data = resp.json()
                token = data.get("accessToken")
                if token:
                    self._access_token = token
                    return token
        except Exception as e:
            logger.warning(f"Gagal mengambil anonymous Spotify token: {e}")
        return None

    def extract(self, url: str) -> Dict[str, Any]:
        """Main entry point to extract metadata from any Spotify URL."""
        parsed = self.parse_url(url)
        item_type = parsed["type"]
        item_id = parsed["id"]

        # Strategy 1: Public Spotify Web API with guest token
        token = self._access_token or self._get_anonymous_token()
        if token:
            try:
                if item_type == "track":
                    return self._extract_track_api(item_id, token)
                elif item_type == "album":
                    return self._extract_album_api(item_id, token)
                elif item_type == "playlist":
                    return self._extract_playlist_api(item_id, token)
            except Exception as e:
                logger.warning(f"Spotify Web API fallback triggered for {item_type}/{item_id}: {e}")

        # Strategy 2: Embed Page Scraping Fallback
        try:
            return self._extract_embed_fallback(item_type, item_id, url)
        except Exception as e:
            logger.warning(f"Embed fallback failed: {e}")

        # Strategy 3: oEmbed (Track fallback)
        if item_type == "track":
            return self._extract_oembed_fallback(url)

        raise RuntimeError(f"Gagal mengekstrak metadata untuk URL Spotify tersebut.")

    def _extract_track_api(self, track_id: str, token: str) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {token}"}
        resp = self.session.get(f"https://api.spotify.com/v1/tracks/{track_id}", headers=headers, timeout=self.timeout)
        if resp.status_code != 200:
            raise RuntimeError(f"API Track error status {resp.status_code}")
        data = resp.json()

        artists = [a["name"] for a in data.get("artists", [])]
        images = data.get("album", {}).get("images", [])
        cover_url = images[0]["url"] if images else ""
        release_date = data.get("album", {}).get("release_date", "")
        year = release_date.split("-")[0] if release_date else ""

        track_info = {
            "id": data["id"],
            "title": data["name"],
            "artists": artists,
            "artist_display": ", ".join(artists),
            "album": data.get("album", {}).get("name", ""),
            "duration_ms": data.get("duration_ms", 0),
            "duration_sec": round(data.get("duration_ms", 0) / 1000),
            "cover_url": cover_url,
            "year": year,
            "track_number": data.get("track_number", 1),
            "spotify_url": data.get("external_urls", {}).get("spotify", f"https://open.spotify.com/track/{track_id}")
        }

        return {
            "type": "track",
            "title": track_info["title"],
            "artists": artists,
            "artist_display": track_info["artist_display"],
            "cover_url": cover_url,
            "total_tracks": 1,
            "tracks": [track_info]
        }

    def _extract_album_api(self, album_id: str, token: str) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {token}"}
        resp = self.session.get(f"https://api.spotify.com/v1/albums/{album_id}", headers=headers, timeout=self.timeout)
        if resp.status_code != 200:
            raise RuntimeError(f"API Album error status {resp.status_code}")
        data = resp.json()

        artists = [a["name"] for a in data.get("artists", [])]
        images = data.get("images", [])
        cover_url = images[0]["url"] if images else ""
        release_date = data.get("release_date", "")
        year = release_date.split("-")[0] if release_date else ""
        album_name = data.get("name", "")

        tracks: List[Dict[str, Any]] = []
        for item in data.get("tracks", {}).get("items", []):
            t_artists = [a["name"] for a in item.get("artists", [])]
            tracks.append({
                "id": item["id"],
                "title": item["name"],
                "artists": t_artists,
                "artist_display": ", ".join(t_artists),
                "album": album_name,
                "duration_ms": item.get("duration_ms", 0),
                "duration_sec": round(item.get("duration_ms", 0) / 1000),
                "cover_url": cover_url,
                "year": year,
                "track_number": item.get("track_number", len(tracks) + 1),
                "spotify_url": item.get("external_urls", {}).get("spotify", f"https://open.spotify.com/track/{item['id']}")
            })

        return {
            "type": "album",
            "title": album_name,
            "artists": artists,
            "artist_display": ", ".join(artists),
            "cover_url": cover_url,
            "year": year,
            "total_tracks": len(tracks),
            "tracks": tracks
        }

    def _extract_playlist_api(self, playlist_id: str, token: str) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {token}"}
        resp = self.session.get(f"https://api.spotify.com/v1/playlists/{playlist_id}", headers=headers, timeout=self.timeout)
        if resp.status_code != 200:
            raise RuntimeError(f"API Playlist error status {resp.status_code}")
        data = resp.json()

        owner = data.get("owner", {}).get("display_name", "Spotify")
        images = data.get("images", [])
        cover_url = images[0]["url"] if images else ""
        playlist_name = data.get("name", "Playlist")

        tracks: List[Dict[str, Any]] = []
        for idx, item in enumerate(data.get("tracks", {}).get("items", [])):
            t = item.get("track")
            if not t or not t.get("id"):
                continue
            t_artists = [a["name"] for a in t.get("artists", [])]
            t_images = t.get("album", {}).get("images", [])
            t_cover = t_images[0]["url"] if t_images else cover_url
            release_date = t.get("album", {}).get("release_date", "")
            year = release_date.split("-")[0] if release_date else ""

            tracks.append({
                "id": t["id"],
                "title": t["name"],
                "artists": t_artists,
                "artist_display": ", ".join(t_artists),
                "album": t.get("album", {}).get("name", playlist_name),
                "duration_ms": t.get("duration_ms", 0),
                "duration_sec": round(t.get("duration_ms", 0) / 1000),
                "cover_url": t_cover,
                "year": year,
                "track_number": idx + 1,
                "spotify_url": t.get("external_urls", {}).get("spotify", f"https://open.spotify.com/track/{t['id']}")
            })

        return {
            "type": "playlist",
            "title": playlist_name,
            "artists": [owner],
            "artist_display": owner,
            "cover_url": cover_url,
            "total_tracks": len(tracks),
            "tracks": tracks
        }

    def _extract_embed_fallback(self, item_type: str, item_id: str, raw_url: str) -> Dict[str, Any]:
        """Scrape Spotify embed HTML containing Next.js or entity state."""
        embed_url = f"https://open.spotify.com/embed/{item_type}/{item_id}"
        resp = self.session.get(embed_url, timeout=self.timeout)
        if resp.status_code != 200:
            raise RuntimeError(f"Embed page returned status {resp.status_code}")

        html = resp.text
        # Look for JSON payload in script
        match = re.search(r'<script id="__NEXT_DATA__" type="application/json">([^<]+)</script>', html)
        if not match:
            # Alternate search pattern for Spotify entity
            match = re.search(r'<script id="initial-state" type="text/plain">([^<]+)</script>', html)

        if match:
            data = json.loads(match.group(1))
            # Extract props
            entity = (
                data.get("props", {}).get("pageProps", {}).get("state", {}).get("data", {}).get("entity")
                or data.get("props", {}).get("pageProps", {}).get("entity")
            )
            if entity:
                title = entity.get("title") or entity.get("name", "")
                cover = entity.get("coverArt", {}).get("sources", [{}])[0].get("url", "")
                
                if item_type == "track":
                    artists = [a.get("name", "") for a in entity.get("artists", [])]
                    track = {
                        "id": item_id,
                        "title": title,
                        "artists": artists,
                        "artist_display": ", ".join(artists),
                        "album": entity.get("album", {}).get("name", ""),
                        "duration_ms": entity.get("duration", 0),
                        "duration_sec": round(entity.get("duration", 0) / 1000),
                        "cover_url": cover,
                        "year": str(entity.get("releaseDate", {}).get("year", "")),
                        "track_number": 1,
                        "spotify_url": raw_url
                    }
                    return {
                        "type": "track",
                        "title": title,
                        "artists": artists,
                        "artist_display": ", ".join(artists),
                        "cover_url": cover,
                        "total_tracks": 1,
                        "tracks": [track]
                    }

        raise RuntimeError("Gagal mengurai state dari halaman embed Spotify.")

    def _extract_oembed_fallback(self, url: str) -> Dict[str, Any]:
        """Last resort oEmbed fallback for single tracks."""
        resp = self.session.get(f"https://open.spotify.com/oembed?url={url}", timeout=self.timeout)
        if resp.status_code != 200:
            raise RuntimeError(f"oEmbed API returned {resp.status_code}")
        data = resp.json()

        title = data.get("title", "")
        author = data.get("author_name", "")
        thumbnail = data.get("thumbnail_url", "")
        parsed = self.parse_url(url)

        track = {
            "id": parsed["id"],
            "title": title,
            "artists": [author] if author else [],
            "artist_display": author,
            "album": "",
            "duration_ms": 0,
            "duration_sec": 0,
            "cover_url": thumbnail,
            "year": "",
            "track_number": 1,
            "spotify_url": url
        }

        return {
            "type": "track",
            "title": title,
            "artists": [author] if author else [],
            "artist_display": author,
            "cover_url": thumbnail,
            "total_tracks": 1,
            "tracks": [track]
        }
