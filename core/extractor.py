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
    """Zero-auth Spotify metadata extractor supporting Track, Album, and Playlist."""

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

    def parse_url(self, url: str) -> Dict[str, str]:
        """Validate and extract item type and ID from Spotify URL."""
        match = SPOTIFY_URL_PATTERN.search(url)
        if not match:
            raise ValueError("URL Spotify tidak valid. Gunakan format track, album, atau playlist Spotify.")
        return {"type": match.group("type"), "id": match.group("id")}

    def _extract_cover_art(self, entity: Dict[str, Any], url: str) -> str:
        """Find highest resolution cover art from entity state or oEmbed."""
        # 1. visualIdentity images (usually includes 640x640 HD)
        images = entity.get("visualIdentity", {}).get("image", [])
        if images and isinstance(images, list):
            sorted_imgs = sorted(images, key=lambda x: x.get("maxWidth", 0) or x.get("maxHeight", 0), reverse=True)
            for img in sorted_imgs:
                if img.get("url"):
                    return img["url"]

        # 2. coverArt sources
        sources = entity.get("coverArt", {}).get("sources", [])
        if sources and isinstance(sources, list):
            for src in sources:
                if src.get("url"):
                    return src["url"]

        # 3. direct images list
        direct_imgs = entity.get("images", [])
        if direct_imgs and isinstance(direct_imgs, list):
            for img in direct_imgs:
                if img.get("url"):
                    return img["url"]

        # 4. Fallback: oEmbed
        try:
            oembed_resp = self.session.get(f"https://open.spotify.com/oembed?url={url}", timeout=self.timeout)
            if oembed_resp.status_code == 200:
                thumb = oembed_resp.json().get("thumbnail_url")
                if thumb:
                    return thumb
        except Exception as e:
            logger.debug(f"oEmbed fallback error: {e}")

        return ""

    def extract(self, url: str) -> Dict[str, Any]:
        """Main extraction method using Spotify Embed Next.js data with oEmbed fallback."""
        parsed = self.parse_url(url)
        item_type = parsed["type"]
        item_id = parsed["id"]

        embed_url = f"https://open.spotify.com/embed/{item_type}/{item_id}"
        resp = self.session.get(embed_url, timeout=self.timeout)

        if resp.status_code == 200:
            m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', resp.text, re.DOTALL)
            if m:
                try:
                    data = json.loads(m.group(1))
                    props = data.get("props", {}).get("pageProps", {})
                    entity = props.get("state", {}).get("data", {}).get("entity", {}) or props.get("entity", {})
                    if entity:
                        if item_type == "track":
                            return self._parse_embed_track(entity, item_id, url)
                        elif item_type == "album":
                            return self._parse_embed_album(entity, item_id, url)
                        elif item_type == "playlist":
                            return self._parse_embed_playlist(entity, item_id, url)
                except Exception as e:
                    logger.warning(f"Error parsing Spotify embed data: {e}")

        # Fallback for single track: oEmbed
        if item_type == "track":
            return self._extract_oembed_fallback(url)

        raise RuntimeError("Gagal mengekstrak metadata Spotify. Pastikan link lagu/album/playlist bersifat publik.")

    def _parse_embed_track(self, entity: Dict[str, Any], track_id: str, raw_url: str) -> Dict[str, Any]:
        title = entity.get("name") or entity.get("title", "Unknown Track")
        cover_url = self._extract_cover_art(entity, raw_url)

        artists_raw = entity.get("artists", [])
        if artists_raw and isinstance(artists_raw, list):
            artists = [a.get("name", "") for a in artists_raw if a.get("name")]
        else:
            sub = entity.get("subtitle", "")
            artists = [s.strip() for s in sub.split(",") if s.strip()] if sub else ["Spotify Artist"]

        artist_display = ", ".join(artists)
        duration_ms = entity.get("duration", 0)
        release_date = str(entity.get("releaseDate", {}).get("year", "")) if isinstance(entity.get("releaseDate"), dict) else str(entity.get("releaseDate", ""))

        track = {
            "id": track_id,
            "title": title,
            "artists": artists,
            "artist_display": artist_display,
            "album": entity.get("album", {}).get("name", "") if isinstance(entity.get("album"), dict) else title,
            "duration_ms": duration_ms,
            "duration_sec": round(duration_ms / 1000) if duration_ms else 0,
            "cover_url": cover_url,
            "year": release_date,
            "track_number": 1,
            "spotify_url": raw_url
        }

        return {
            "type": "track",
            "title": title,
            "artists": artists,
            "artist_display": artist_display,
            "album": track["album"],
            "year": release_date,
            "cover_url": cover_url,
            "total_tracks": 1,
            "tracks": [track]
        }

    def _parse_embed_album(self, entity: Dict[str, Any], album_id: str, raw_url: str) -> Dict[str, Any]:
        title = entity.get("name") or entity.get("title", "Unknown Album")
        cover_url = self._extract_cover_art(entity, raw_url)

        artists_raw = entity.get("artists", [])
        if artists_raw and isinstance(artists_raw, list):
            artists = [a.get("name", "") for a in artists_raw if a.get("name")]
        else:
            sub = entity.get("subtitle", "")
            artists = [s.strip() for s in sub.split(",") if s.strip()] if sub else ["Artist"]

        artist_display = ", ".join(artists)
        release_date = str(entity.get("releaseDate", {}).get("year", "")) if isinstance(entity.get("releaseDate"), dict) else str(entity.get("releaseDate", ""))

        raw_tracks = entity.get("trackList", [])
        tracks: List[Dict[str, Any]] = []

        for idx, item in enumerate(raw_tracks):
            t_uri = item.get("uri", "")
            t_id = t_uri.split(":")[-1] if ":" in t_uri else f"{album_id}_{idx+1}"
            t_title = item.get("title", f"Track {idx+1}")
            t_sub = item.get("subtitle") or artist_display
            t_artists = [s.strip() for s in t_sub.split(",") if s.strip()]
            t_dur = item.get("duration", 0)

            tracks.append({
                "id": t_id,
                "title": t_title,
                "artists": t_artists,
                "artist_display": t_sub,
                "album": title,
                "duration_ms": t_dur,
                "duration_sec": round(t_dur / 1000) if t_dur else 0,
                "cover_url": cover_url,
                "year": release_date,
                "track_number": idx + 1,
                "spotify_url": f"https://open.spotify.com/track/{t_id}"
            })

        return {
            "type": "album",
            "title": title,
            "artists": artists,
            "artist_display": artist_display,
            "album": title,
            "year": release_date,
            "cover_url": cover_url,
            "total_tracks": len(tracks),
            "tracks": tracks
        }

    def _parse_embed_playlist(self, entity: Dict[str, Any], playlist_id: str, raw_url: str) -> Dict[str, Any]:
        title = entity.get("name") or entity.get("title", "Unknown Playlist")
        cover_url = self._extract_cover_art(entity, raw_url)
        owner = entity.get("subtitle") or "Spotify Playlist"

        raw_tracks = entity.get("trackList", [])
        tracks: List[Dict[str, Any]] = []

        for idx, item in enumerate(raw_tracks):
            t_uri = item.get("uri", "")
            t_id = t_uri.split(":")[-1] if ":" in t_uri else f"{playlist_id}_{idx+1}"
            t_title = item.get("title", f"Track {idx+1}")
            t_sub = item.get("subtitle") or "Various Artists"
            t_artists = [s.strip() for s in t_sub.split(",") if s.strip()]
            t_dur = item.get("duration", 0)

            tracks.append({
                "id": t_id,
                "title": t_title,
                "artists": t_artists,
                "artist_display": t_sub,
                "album": title,
                "duration_ms": t_dur,
                "duration_sec": round(t_dur / 1000) if t_dur else 0,
                "cover_url": cover_url,
                "year": "",
                "track_number": idx + 1,
                "spotify_url": f"https://open.spotify.com/track/{t_id}"
            })

        return {
            "type": "playlist",
            "title": title,
            "artists": [owner],
            "artist_display": owner,
            "cover_url": cover_url,
            "total_tracks": len(tracks),
            "tracks": tracks
        }

    def _extract_oembed_fallback(self, url: str) -> Dict[str, Any]:
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
