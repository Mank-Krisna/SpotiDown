import os
import re
import logging
from typing import Dict, Any, Optional
import yt_dlp

from core.tagger import AudioTagger

logger = logging.getLogger(__name__)

class AudioDownloader:
    """Download audio from YouTube matching Spotify metadata and transcode to desired format."""

    SUPPORTED_FORMATS = {"mp3", "wav", "flac", "m4a"}

    def __init__(self, download_dir: str = "downloads"):
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)
        self.tagger = AudioTagger()

    @staticmethod
    def sanitize_filename(name: str) -> str:
        """Strip illegal filesystem characters for Windows/Linux."""
        # Remove <>:"/\|?*
        cleaned = re.sub(r'[<>:"/\\|?*]', '', name)
        # Collapse multiple spaces
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned or "audio"

    def _get_ydl_opts(self, output_template: str, fmt: str) -> Dict[str, Any]:
        """Construct yt-dlp options based on target audio format."""
        ydl_opts: Dict[str, Any] = {
            "format": "bestaudio/best",
            "outtmpl": output_template,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "default_search": "ytsearch1",
            "postprocessors": [],
        }

        fmt = fmt.lower()
        if fmt == "mp3":
            ydl_opts["postprocessors"].append({
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",
            })
        elif fmt == "wav":
            ydl_opts["postprocessors"].append({
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
            })
        elif fmt == "flac":
            ydl_opts["postprocessors"].append({
                "key": "FFmpegExtractAudio",
                "preferredcodec": "flac",
            })
        elif fmt == "m4a":
            ydl_opts["postprocessors"].append({
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
                "preferredquality": "256",
            })

        return ydl_opts

    def download_track(
        self,
        track_meta: Dict[str, Any],
        fmt: str = "mp3",
        tag: bool = True
    ) -> Dict[str, Any]:
        """Search YouTube, download, transcode, tag, and return file info."""
        fmt = fmt.lower()
        if fmt not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Format {fmt} tidak didukung. Pilihan: {', '.join(self.SUPPORTED_FORMATS)}")

        artist = track_meta.get("artist_display") or (track_meta.get("artists", [""])[0] if track_meta.get("artists") else "")
        title = track_meta.get("title", "Track")
        
        base_name = self.sanitize_filename(f"{artist} - {title}")
        output_tmpl = os.path.join(self.download_dir, f"{base_name}.%(ext)s")
        final_file_path = os.path.join(self.download_dir, f"{base_name}.{fmt}")

        # Search query
        query = f"ytsearch1:{artist} - {title} Official Audio"

        ydl_opts = self._get_ydl_opts(output_tmpl, fmt)

        logger.info(f"Downloading: {query} -> {final_file_path}")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(query, download=True)
                if not info or not info.get("entries"):
                    # Fallback query without "Official Audio"
                    fallback_query = f"ytsearch1:{artist} - {title}"
                    logger.info(f"Fallback search: {fallback_query}")
                    info = ydl.extract_info(fallback_query, download=True)

            if not os.path.exists(final_file_path):
                # Search for any file with base_name
                candidates = [
                    os.path.join(self.download_dir, f)
                    for f in os.listdir(self.download_dir)
                    if f.startswith(base_name) and f.endswith(f".{fmt}")
                ]
                if candidates:
                    final_file_path = candidates[0]
                else:
                    raise RuntimeError(f"File hasil unduhan {final_file_path} tidak ditemukan setelah transcode.")

            # Tag metadata
            if tag:
                try:
                    self.tagger.tag_file(final_file_path, track_meta, fmt)
                except Exception as e:
                    logger.warning(f"Gagal menyematkan metadata ke {final_file_path}: {e}")

            file_size = os.path.getsize(final_file_path)

            return {
                "success": True,
                "file_path": final_file_path,
                "filename": os.path.basename(final_file_path),
                "file_size": file_size,
                "format": fmt,
                "track": track_meta
            }

        except Exception as e:
            logger.error(f"Error saat mengunduh track {title}: {e}")
            raise RuntimeError(f"Gagal mengunduh audio: {str(e)}")
