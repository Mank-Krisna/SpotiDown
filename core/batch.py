import os
import uuid
import zipfile
import logging
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime

from core.downloader import AudioDownloader

logger = logging.getLogger(__name__)

class BatchManager:
    """Manages asynchronous batch downloads for albums and playlists, bundling into ZIP files."""

    def __init__(self, download_dir: str = "downloads"):
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)
        self.downloader = AudioDownloader(download_dir=self.download_dir)
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create_batch_task(
        self,
        collection_title: str,
        tracks: List[Dict[str, Any]],
        fmt: str = "mp3"
    ) -> str:
        """Initialize a new batch task and start background download."""
        task_id = str(uuid.uuid4())
        safe_title = AudioDownloader.sanitize_filename(collection_title)

        with self._lock:
            self.tasks[task_id] = {
                "id": task_id,
                "title": collection_title,
                "safe_title": safe_title,
                "format": fmt.lower(),
                "total_tracks": len(tracks),
                "completed_tracks": 0,
                "current_song": "",
                "status": "pending",  # pending, downloading, packaging, completed, failed
                "error": None,
                "zip_path": None,
                "zip_filename": None,
                "created_at": datetime.now().isoformat(),
                "completed_at": None,
            }

        # Run background thread
        thread = threading.Thread(
            target=self._process_batch,
            args=(task_id, tracks, fmt.lower(), safe_title),
            daemon=True
        )
        thread.start()

        return task_id

    def get_task_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Fetch current status and progress of a task."""
        with self._lock:
            task = self.tasks.get(task_id)
            if not task:
                return None
            return dict(task)

    def _process_batch(
        self,
        task_id: str,
        tracks: List[Dict[str, Any]],
        fmt: str,
        safe_title: str
    ):
        downloaded_files: List[str] = []

        try:
            with self._lock:
                self.tasks[task_id]["status"] = "downloading"

            for idx, track in enumerate(tracks):
                song_name = f"{track.get('artist_display', '')} - {track.get('title', '')}"
                with self._lock:
                    self.tasks[task_id]["current_song"] = song_name

                try:
                    res = self.downloader.download_track(track, fmt=fmt, tag=True)
                    if res.get("file_path") and os.path.exists(res["file_path"]):
                        downloaded_files.append(res["file_path"])
                except Exception as e:
                    logger.warning(f"Batch task {task_id}: Gagal download track '{song_name}': {e}")

                with self._lock:
                    self.tasks[task_id]["completed_tracks"] = idx + 1

            if not downloaded_files:
                raise RuntimeError("Tidak ada lagu yang berhasil diunduh.")

            # Create ZIP archive
            with self._lock:
                self.tasks[task_id]["status"] = "packaging"
                self.tasks[task_id]["current_song"] = "Membuat file ZIP..."

            zip_filename = f"{safe_title}_{fmt.upper()}.zip"
            zip_path = os.path.join(self.download_dir, zip_filename)

            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for file_path in downloaded_files:
                    if os.path.exists(file_path):
                        arcname = os.path.basename(file_path)
                        zipf.write(file_path, arcname=arcname)

            with self._lock:
                self.tasks[task_id]["status"] = "completed"
                self.tasks[task_id]["current_song"] = "Selesai!"
                self.tasks[task_id]["zip_path"] = zip_path
                self.tasks[task_id]["zip_filename"] = zip_filename
                self.tasks[task_id]["completed_at"] = datetime.now().isoformat()

            logger.info(f"Batch task {task_id} selesai: {zip_path}")

        except Exception as e:
            logger.error(f"Batch task {task_id} gagal: {e}")
            with self._lock:
                self.tasks[task_id]["status"] = "failed"
                self.tasks[task_id]["error"] = str(e)
