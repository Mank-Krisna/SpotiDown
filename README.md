# SpotiDown 🎵
> Modern Web-Based Spotify Music Downloader & Metadata Archiver (MP3 320kbps, Lossless WAV, FLAC, M4A)

SpotiDown adalah aplikasi web open-source untuk mengunduh lagu, album, dan playlist Spotify ke format audio berkualitas tinggi (**MP3 320kbps**, **WAV Lossless PCM**, **FLAC**, dan **M4A 256kbps**) lengkap dengan cover artwork HD dan metadata ID3 otomatis tanpa perlu akun Spotify Premium atau pendaftaran Spotify Developer API.

---

## ✨ Fitur Utama

- ⚡ **Zero-Configuration:** Cukup tempel link lagu/album/playlist Spotify publik, tanpa login atau API key.
- 🎧 **Multi-Format Audio:**
  - **MP3 (320 kbps)** - Bitrate tinggi standar
  - **WAV** - Lossless PCM uncompressed murni
  - **FLAC** - Hi-Res lossless audio
  - **M4A (256 kbps)** - Format efisien untuk perangkat Apple
- 🎨 **Cover Art & ID3 Tagging HD:** Menyematkan cover album resolusi penuh (640x640), judul, artis, album, dan tahun rilis ke file audio via `mutagen`.
- 📦 **Batch Downloader (Album & Playlist):** Mengunduh seluruh playlist/album sekaligus dan membundelnya menjadi arsip `.zip`.
- 🌙 **Spotify Dark UI (Glassmorphism):** Antarmuka responsif dan modern dengan preview card, tracklist table, dan live progress tracking.
- 🧹 **Auto-Cleaner:** Pembersihan background otomatis untuk file unduhan temporer yang berusia > 30 menit.

---

## 🚀 Prasyarat & Instalasi

### 1. Prasyarat
- **Python 3.10+**
- **FFmpeg** terinstal dan terdaftar di sistem `PATH`

### 2. Klon & Setup Repository
```bash
git clone https://github.com/Mank-Krisna/SpotiDown.git
cd SpotiDown

# Buat virtual environment
python -m venv .venv

# Aktifkan virtual environment
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

# Install dependensi
pip install -r requirements.txt
```

### 3. Menjalankan Aplikasi
```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```
Buka browser di: **`http://127.0.0.1:8000`**

---

## 🐳 Jalankan via Docker

```bash
# Build Docker image
docker build -t spotidown .

# Jalankan container
docker run -d -p 8000:8000 --name spotidown-app spotidown
```

---

## ☁️ Panduan Deploy ke Cloud (Gratis & Mudah)

### Opsi 1: Render.com (Direkomendasikan)
1. Buka [render.com](https://render.com) dan login dengan akun GitHub kamu.
2. Klik **New +** $\rightarrow$ **Web Service**.
3. Pilih repository **`Mank-Krisna/SpotiDown`**.
4. Render akan otomatis mendeteksi konfigurasi **Docker** dan file `render.yaml`.
5. Klik **Deploy Web Service**. Selesai!

### Opsi 2: Railway.app
1. Buka [railway.app](https://railway.app) dan login dengan GitHub.
2. Klik **New Project** $\rightarrow$ **Deploy from GitHub repo**.
3. Pilih repository **`SpotiDown`**.
4. Railway otomatis mem-build menggunakan `Dockerfile`.

---

## 🛠️ Tech Stack

- **Backend:** FastAPI, Python 3, `yt-dlp`, `mutagen`, `requests`
- **Audio Processing:** `ffmpeg`
- **Frontend:** Vanilla HTML5, CSS3 (Glassmorphism Dark Theme), ES6 JavaScript

---

## 📄 Lisensi
MIT License. Dibuat untuk tujuan edukasi & backup metadata personal.
