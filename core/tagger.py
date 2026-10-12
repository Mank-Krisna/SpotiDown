import os
import logging
from typing import Optional, Dict, Any
import requests

logger = logging.getLogger(__name__)

class AudioTagger:
    """Multi-format audio metadata tagger supporting MP3, FLAC, M4A, and WAV."""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SpotiDown/1.0"
        })

    def _fetch_image_bytes(self, cover_url: Optional[str]) -> Optional[bytes]:
        """Download cover artwork bytes."""
        if not cover_url:
            return None
        try:
            resp = self.session.get(cover_url, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.content
        except Exception as e:
            logger.warning(f"Gagal mengunduh cover image dari {cover_url}: {e}")
        return None

    def tag_file(self, file_path: str, metadata: Dict[str, Any], fmt: str) -> bool:
        """Embed metadata and cover image into audio file based on format."""
        if not os.path.exists(file_path):
            logger.error(f"File tidak ditemukan: {file_path}")
            return False

        fmt = fmt.lower()
        cover_bytes = self._fetch_image_bytes(metadata.get("cover_url"))

        try:
            if fmt == "mp3":
                return self._tag_mp3(file_path, metadata, cover_bytes)
            elif fmt == "flac":
                return self._tag_flac(file_path, metadata, cover_bytes)
            elif fmt == "m4a":
                return self._tag_m4a(file_path, metadata, cover_bytes)
            elif fmt == "wav":
                return self._tag_wav(file_path, metadata, cover_bytes)
            else:
                logger.warning(f"Format {fmt} tidak didukung untuk ID3 tagging.")
                return True
        except Exception as e:
            logger.error(f"Error saat tagging metadata ({fmt}) untuk {file_path}: {e}")
            return False

    def _tag_mp3(self, file_path: str, meta: Dict[str, Any], cover_bytes: Optional[bytes]) -> bool:
        from mutagen.mp3 import MP3
        from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TRCK, APIC, ID3NoHeaderError

        try:
            audio = MP3(file_path, ID3=ID3)
            try:
                audio.add_tags()
            except Exception:
                pass
        except ID3NoHeaderError:
            audio = MP3(file_path)
            audio.add_tags()

        if audio.tags is None:
            audio.tags = ID3()

        if meta.get("title"):
            audio.tags.add(TIT2(encoding=3, text=meta["title"]))
        if meta.get("artist_display"):
            audio.tags.add(TPE1(encoding=3, text=meta["artist_display"]))
        if meta.get("album"):
            audio.tags.add(TALB(encoding=3, text=meta["album"]))
        if meta.get("year"):
            audio.tags.add(TDRC(encoding=3, text=str(meta["year"])))
        if meta.get("track_number"):
            audio.tags.add(TRCK(encoding=3, text=str(meta["track_number"])))

        if cover_bytes:
            audio.tags.add(APIC(
                encoding=3,
                mime="image/jpeg",
                type=3,  # Cover (front)
                desc="Cover",
                data=cover_bytes
            ))

        audio.save(v2_version=3)
        return True

    def _tag_flac(self, file_path: str, meta: Dict[str, Any], cover_bytes: Optional[bytes]) -> bool:
        from mutagen.flac import FLAC, Picture

        audio = FLAC(file_path)
        if meta.get("title"):
            audio["TITLE"] = meta["title"]
        if meta.get("artist_display"):
            audio["ARTIST"] = meta["artist_display"]
        if meta.get("album"):
            audio["ALBUM"] = meta["album"]
        if meta.get("year"):
            audio["DATE"] = str(meta["year"])
        if meta.get("track_number"):
            audio["TRACKNUMBER"] = str(meta["track_number"])

        if cover_bytes:
            image = Picture()
            image.type = 3
            image.mime = "image/jpeg"
            image.desc = "Cover"
            image.data = cover_bytes
            audio.clear_pictures()
            audio.add_picture(image)

        audio.save()
        return True

    def _tag_m4a(self, file_path: str, meta: Dict[str, Any], cover_bytes: Optional[bytes]) -> bool:
        from mutagen.mp4 import MP4, MP4Cover

        audio = MP4(file_path)
        if meta.get("title"):
            audio["\xa9nam"] = meta["title"]
        if meta.get("artist_display"):
            audio["\xa9ART"] = meta["artist_display"]
        if meta.get("album"):
            audio["\xa9alb"] = meta["album"]
        if meta.get("year"):
            audio["\xa9day"] = str(meta["year"])
        if meta.get("track_number"):
            try:
                audio["trkn"] = [(int(meta["track_number"]), 0)]
            except Exception:
                pass

        if cover_bytes:
            audio["covr"] = [MP4Cover(cover_bytes, imageformat=MP4Cover.FORMAT_JPEG)]

        audio.save()
        return True

    def _tag_wav(self, file_path: str, meta: Dict[str, Any], cover_bytes: Optional[bytes]) -> bool:
        from mutagen.wave import WAVE
        from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TRCK, APIC

        try:
            audio = WAVE(file_path)
            try:
                audio.add_tags()
            except Exception:
                pass
            if audio.tags is None:
                audio.tags = ID3()

            if meta.get("title"):
                audio.tags.add(TIT2(encoding=3, text=meta["title"]))
            if meta.get("artist_display"):
                audio.tags.add(TPE1(encoding=3, text=meta["artist_display"]))
            if meta.get("album"):
                audio.tags.add(TALB(encoding=3, text=meta["album"]))
            if meta.get("year"):
                audio.tags.add(TDRC(encoding=3, text=str(meta["year"])))
            if meta.get("track_number"):
                audio.tags.add(TRCK(encoding=3, text=str(meta["track_number"])))

            if cover_bytes:
                audio.tags.add(APIC(
                    encoding=3,
                    mime="image/jpeg",
                    type=3,
                    desc="Cover",
                    data=cover_bytes
                ))
            audio.save()
            return True
        except Exception as e:
            logger.warning(f"Tagging WAV RIFF header warning: {e}")
            return True
