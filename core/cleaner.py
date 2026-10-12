import os
import time
import logging
import threading

logger = logging.getLogger(__name__)

class AutoCleaner:
    """Periodically cleans up temporary audio and zip files older than TTL."""

    def __init__(self, directory: str = "downloads", ttl_seconds: int = 1800, check_interval: int = 300):
        self.directory = directory
        self.ttl_seconds = ttl_seconds
        self.check_interval = check_interval
        self._running = False
        self._thread = None

    def start(self):
        """Start cleaner daemon thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info(f"AutoCleaner aktif untuk '{self.directory}' (TTL: {self.ttl_seconds}s)")

    def stop(self):
        """Stop cleaner thread."""
        self._running = False

    def clean_once(self) -> int:
        """Run a single cleanup pass, returns number of deleted files."""
        if not os.path.exists(self.directory):
            return 0

        now = time.time()
        deleted_count = 0

        for root, _, files in os.walk(self.directory):
            for f in files:
                file_path = os.path.join(root, f)
                try:
                    stat = os.stat(file_path)
                    file_age = now - stat.st_mtime
                    if file_age > self.ttl_seconds:
                        os.remove(file_path)
                        deleted_count += 1
                        logger.info(f"AutoCleaner: Hapus file usang {file_path} ({round(file_age/60)} menit)")
                except Exception as e:
                    logger.warning(f"AutoCleaner gagal menghapus {file_path}: {e}")

        return deleted_count

    def _run_loop(self):
        while self._running:
            try:
                self.clean_once()
            except Exception as e:
                logger.error(f"AutoCleaner error: {e}")
            time.sleep(self.check_interval)
