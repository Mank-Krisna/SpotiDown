import os
import logging
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.extractor import SpotifyExtractor
from core.downloader import AudioDownloader
from core.batch import BatchManager
from core.cleaner import AutoCleaner

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("spotidown")

# Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
STATIC_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# Engines
extractor = SpotifyExtractor()
downloader = AudioDownloader(download_dir=DOWNLOAD_DIR)
batch_manager = BatchManager(download_dir=DOWNLOAD_DIR)
cleaner = AutoCleaner(directory=DOWNLOAD_DIR, ttl_seconds=1800, check_interval=300)

@asynccontextmanager
async def lifespan(app: FastAPI):
    cleaner.start()
    yield
    cleaner.stop()

app = FastAPI(
    title="SpotiDown API",
    description="Spotify to High-Quality Multi-Format Audio Downloader",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Models
class InfoRequest(BaseModel):
    url: str = Field(..., description="Spotify Track, Album, or Playlist URL")

class TrackDownloadRequest(BaseModel):
    url: Optional[str] = None
    track: Optional[Dict[str, Any]] = None
    format: str = Field(default="mp3", description="Audio format: mp3, wav, flac, or m4a")

class BatchDownloadRequest(BaseModel):
    title: str = Field(..., description="Collection/Album/Playlist title")
    tracks: List[Dict[str, Any]] = Field(..., description="List of track metadata objects")
    format: str = Field(default="mp3", description="Audio format: mp3, wav, flac, or m4a")

# Endpoints
@app.post("/api/info")
async def get_info(req: InfoRequest):
    """Fetch Spotify metadata for track, album, or playlist."""
    try:
        data = extractor.extract(req.url.strip())
        return data
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error extracting metadata: {e}")
        raise HTTPException(status_code=500, detail=f"Gagal mengambil metadata Spotify: {str(e)}")

@app.post("/api/download/track")
async def download_single_track(req: TrackDownloadRequest):
    """Download a single track and return download URL."""
    try:
        fmt = req.format.lower()
        if fmt not in AudioDownloader.SUPPORTED_FORMATS:
            raise HTTPException(status_code=400, detail=f"Format tidak valid. Pilihan: {list(AudioDownloader.SUPPORTED_FORMATS)}")

        track_meta = req.track
        if not track_meta and req.url:
            extracted = extractor.extract(req.url.strip())
            if not extracted.get("tracks"):
                raise HTTPException(status_code=404, detail="Lagu tidak ditemukan pada URL tersebut.")
            track_meta = extracted["tracks"][0]

        if not track_meta:
            raise HTTPException(status_code=400, detail="Data track atau URL Spotify diperlukan.")

        result = downloader.download_track(track_meta, fmt=fmt, tag=True)
        filename = result["filename"]

        return {
            "success": True,
            "filename": filename,
            "format": fmt,
            "file_size": result["file_size"],
            "download_url": f"/api/file/{filename}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download single track failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/download/batch")
async def start_batch_download(req: BatchDownloadRequest):
    """Trigger background batch download for album/playlist."""
    try:
        fmt = req.format.lower()
        if fmt not in AudioDownloader.SUPPORTED_FORMATS:
            raise HTTPException(status_code=400, detail=f"Format tidak valid. Pilihan: {list(AudioDownloader.SUPPORTED_FORMATS)}")

        if not req.tracks:
            raise HTTPException(status_code=400, detail="Daftar lagu tidak boleh kosong.")

        task_id = batch_manager.create_batch_task(
            collection_title=req.title,
            tracks=req.tracks,
            fmt=fmt
        )

        return {
            "task_id": task_id,
            "status": "pending",
            "total_tracks": len(req.tracks),
            "format": fmt
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch task creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/progress/{task_id}")
async def get_progress(task_id: str):
    """Check batch download job progress."""
    progress = batch_manager.get_task_progress(task_id)
    if not progress:
        raise HTTPException(status_code=404, detail="Task ID tidak ditemukan.")
    
    if progress.get("zip_filename"):
        progress["download_url"] = f"/api/file/{progress['zip_filename']}"

    return progress

@app.get("/api/file/{filename}")
async def serve_file(filename: str):
    """Serve downloaded audio file or ZIP archive."""
    # Prevent directory traversal
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(DOWNLOAD_DIR, safe_filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File tidak ditemukan atau telah kedaluwarsa.")

    return FileResponse(
        path=file_path,
        filename=safe_filename,
        media_type="application/octet-stream"
    )

@app.get("/sw.js")
async def kill_service_worker():
    """Unregister any stale service worker from past projects on this domain."""
    from fastapi.responses import Response
    content = """
    self.addEventListener('install', (e) => { self.skipWaiting(); });
    self.addEventListener('activate', (e) => {
        self.registration.unregister().then(() => {
            return self.clients.matchAll();
        }).then((clients) => {
            clients.forEach(client => client.navigate(client.url));
        });
    });
    """
    return Response(content=content, media_type="application/javascript")

# Static files mount & root index
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "SpotiDown API is running. Place index.html into static/ folder."}
