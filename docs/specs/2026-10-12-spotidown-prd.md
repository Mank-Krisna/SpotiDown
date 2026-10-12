# Product Requirements Document (PRD) & Technical Design
## Project: SpotiDown (Web-Based Spotify Music Downloader)
**Date:** 2026-10-12  
**Status:** Approved for Implementation  
**Version:** 1.0.0  

---

### 1. Executive Summary & Vision
SpotiDown adalah aplikasi web open-source modern yang memungkinkan pengguna mengambil audio MP3 berkualitas tinggi (hingga 320 kbps) dari tautan Spotify (Track, Album, dan Playlist) secara otomatis tanpa memerlukan akun Spotify Premium maupun pendaftaran Spotify Developer API key.

Aplikasi ini meniru pengalaman pengguna layanan populer seperti *SpotiSaver.net*, dengan antarmuka web modern (*Spotify Dark Aesthetic*), ekstraksi metadata instan, pencarian audio pencocok via YouTube/YT Music menggunakan `yt-dlp`, serta penyuntikan metadata ID3v2 lengkap (judul, artis, album, tahun, dan cover art HD).

---

### 2. Goals & Non-Goals

#### 2.1 Goals
- **Zero-Configuration User Experience:** Pengguna cukup menempelkan URL Spotify publik tanpa login atau input kredensial.
- **Dukungan Format Spotify Lengkap:** Mendukung Spotify Track, Album, dan Playlist.
- **Pilihan Format Audio Luas (Multi-Format):** 
  - **MP3** (hingga 320 kbps - Default populer)
  - **WAV** (Lossless PCM uncompressed - Audio murni tanpa kompresi)
  - **FLAC** (Lossless compressed audio)
  - **M4A / AAC** (Kualitas tinggi efisien)
- **Metadata Sempurna:** Tag metadata tertanam rapi (Title, Artist, Album, Year, Track Number, High-Res Cover Art) sesuai standar format audio (ID3v2 untuk MP3/WAV, Vorbis untuk FLAC, MP4 Tags untuk M4A).
- **Batch Processing:** Mendukung pengunduhan batch untuk Album/Playlist yang dibundel ke dalam arsip `.zip`.
- **UI Responsif & Interaktif:** Tampilan web responsif dengan preview track/cover art, selector format audio, progress bar real-time, dan status proses transparan.

#### 2.2 Non-Goals (Out of Scope v1)
- Membobol enkripsi DRM Spotify secara langsung (audio dicocokkan dan diambil secara legal dari sumber publik YouTube/YouTube Music).
- Penyimpanan permanen file musik di server (file disimpan di cache lokal temporer dan dihapus setelah diunduh atau melewati TTL).
- Akun pengguna / sistem registrasi (layanan bersifat instan & stateless).

---

### 3. System Architecture & Component Design

```
[ Web Browser (User) ]
       │  ▲
       │  │ (HTTP REST / Server-Sent Events)
       ▼  │
┌────────────────────────────────────────────────────────┐
│ FastAPI Application Server (main.py)                   │
├────────────────────────────────────────────────────────┤
│  1. API Router & Static File Handler                   │
│     - GET  /                    -> Serve Web UI        │
│     - POST /api/info            -> Fetch Track/List    │
│     - POST /api/download/track  -> Single MP3 Stream   │
│     - POST /api/download/batch  -> Trigger Batch Job   │
│     - GET  /api/progress/{id}   -> Stream Job Progress │
│     - GET  /api/file/{id}       -> Download File/Zip   │
│                                                        │
│  2. Core Engine Modules                                │
│     ├── extractor.py    (Scrape Spotify Metadata)      │
│     ├── downloader.py   (yt-dlp search & MP3 encode)   │
│     ├── tagger.py       (Mutagen ID3v2 & Cover Art)    │
│     ├── batch.py        (Multi-track queue & ZIP packaging)
│     └── cleaner.py      (Auto-delete temp files > TTL) │
└────────────────────────────────────────────────────────┘
       │                                     │
       ▼                                     ▼
[ Spotify Public Web / oEmbed ]     [ YouTube / YT Music Stream ]
(Metadata & Cover Art Image)        (Audio Stream via yt-dlp + ffmpeg)
```

---

### 4. Detailed Component Specifications

#### 4.1 Metadata Extractor (`extractor.py`)
- **Fungsi:** Mengurai URL Spotify (`https://open.spotify.com/track/...`, `album/...`, `playlist/...`).
- **Mekanisme Ekstraksi:**
  - Track sederhana: Menggunakan Spotify oEmbed API (`https://open.spotify.com/oembed?url=...`) dan Spotify embed page scraping tanpa otentikasi.
  - Album & Playlist: Mengambil Spotify anonymous web token (`https://open.spotify.com/get_access_token`) untuk query public Spotify Web API partner endpoint, mengekstrak seluruh daftar lagu beserta durasi, artis, dan cover art resolusi tinggi.
- **Output Schema:**
  ```json
  {
    "type": "track" | "album" | "playlist",
    "title": "Song / Album Name",
    "artists": ["Artist Name"],
    "cover_url": "https://i.scdn.co/image/...",
    "total_tracks": 1,
    "tracks": [
      {
        "id": "spotify_id",
        "title": "Song Title",
        "artists": ["Artist"],
        "album": "Album Name",
        "duration_ms": 210000,
        "cover_url": "https://i.scdn.co/image/..."
      }
    ]
  }
  ```

#### 4.2 Audio Matcher & Downloader (`downloader.py`)
- **Fungsi:** Mengambil audio dari YouTube berdasarkan pencocokan metadata Spotify.
- **Search Strategy:**
  - Query default: `"{Artist} - {Title} Audio"`
  - Menggunakan `yt-dlp` native Python API dengan opsi `default_search: "ytsearch1"`.
- **Audio Extraction & Encoding:**
  - Ekstraksi dan konversi audio menggunakan backend `ffmpeg`.
  - Pilihan format target yang didukung:
    - **MP3:** Bitrate 320 kbps (CBR/VBR high quality `libmp3lame`).
    - **WAV:** 16-bit PCM uncompressed lossless (`pcm_s16le`).
    - **FLAC:** Lossless compression level 5 (`flac`).
    - **M4A / AAC:** Bitrate 256 kbps (`aac`).
  - Penyesuaian durasi: Memastikan durasi audio YouTube tidak terpaut lebih dari $\pm 15$ detik dari durasi lagu Spotify guna menghindari versi podcast/live/music video intro panjang.

#### 4.3 Metadata Tagger (`tagger.py`)
- **Fungsi:** Menyematkan metadata standar dan album artwork ke file audio sesuai formatnya menggunakan pustaka `mutagen`.
- **Dukungan Format Tag:**
  - **MP3 & WAV:** ID3v2.3/ID3v2.4 tags (`TIT2`, `TPE1`, `TALB`, `TYER`, `APIC` Cover Art).
  - **FLAC:** Vorbis Comments (`TITLE`, `ARTIST`, `ALBUM`, `DATE`) + `Picture` block untuk cover art HD.
  - **M4A (MP4 container):** Apple iTunes metadata atom (`\xa9nam`, `\xa9ART`, `\xa9alb`, `\xa9day`, `covr` artwork).

#### 4.4 Batch Manager & Zip Bundler (`batch.py`)
- **Fungsi:** Mengelola antrean unduhan saat pengguna memilih mengunduh seluruh Album atau Playlist dalam format yang dipilih.
- **Workflow:**
  - Menerima parameter format audio yang diinginkan (`mp3`, `wav`, `flac`, atau `m4a`).
  - Membuat `task_id` unik (UUIDv4).
  - Menjalankan background worker asinkron:
    - Download track demi track sesuai format terpilih (maksimal 2 worker paralel untuk mencegah rate limit).
    - Memperbarui progres (`completed_tracks`, `total_tracks`, `current_song`, `format`).
    - Setelah semua selesai, bundel seluruh file audio ke dalam satu file ZIP: `"{Album/Playlist Name}_{FORMAT}.zip"`.
  - Mengirim progres ke frontend melalui polling endpoint `/api/progress/{task_id}`.

#### 4.5 Auto Cleaner (`cleaner.py`)
- **Fungsi:** Mencegah pembengkakan penyimpanan disk lokal.
- **Aturan:** File audio (`.mp3`, `.wav`, `.flac`, `.m4a`) dan file `.zip` di direktori `downloads/` yang usianya lebih dari 30 menit akan dihapus secara otomatis melalui background task berkala.

#### 4.6 Frontend Web UI (`static/index.html`, `static/style.css`, `static/app.js`)
- **Design Language:** Spotify-inspired dark UI, Glassmorphism, aksen hijau Spotify (`#1DB954`), tipografi modern (Inter/Circular).
- **Fitur Antarmuka:**
  - Input field responsif dengan tombol "Fetch / Analisa".
  - Card Preview: Menampilkan cover art HD, judul lagu/album, nama artis, dan badge jumlah lagu.
  - **Format Selector:** Segmented control / dropdown interaktif untuk memilih format unduhan (**MP3**, **WAV**, **FLAC**, **M4A**).
  - Playlist Tracklist Table: Tabel scrollable dengan nomor lagu, judul, durasi, dan tombol unduh individual per lagu sesuai format terpilih.
  - Global Actions: Tombol "Download {FORMAT}" untuk single track, atau "Download All (ZIP)" untuk album/playlist.
  - Live Progress Indicator: Progress bar dinamis, persentase unduhan, dan status text ("Mencari audio...", "Mengunduh...", "Menyematkan cover art...", "Selesai").
  - Toast Notification: Notifikasi error ramah pengguna jika link tidak valid atau audio gagal diunduh.

---

### 5. API Endpoints Specification

| Method | Endpoint | Deskripsi | Parameter / Payload |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Melayani web frontend | - |
| `POST` | `/api/info` | Ekstrak metadata dari URL Spotify | `{"url": "https://open.spotify.com/..."}` |
| `POST` | `/api/download/track` | Download 1 track langsung | `{"url": "...", "track_id": "...", "format": "mp3"|"wav"|"flac"|"m4a"}` |
| `POST` | `/api/download/batch` | Memulai proses batch unduhan album/playlist | `{"url": "...", "tracks": [...], "format": "mp3"|"wav"|"flac"|"m4a"}` |
| `GET` | `/api/progress/{task_id}` | Cek status dan progres batch job | `task_id` (Path param) |
| `GET` | `/api/file/{file_id}` | Mengunduh hasil file audio atau ZIP | `file_id` (Path param) |

---

### 6. Dependency & Environmental Requirements

- **Python Runtime:** Python 3.10 atau lebih baru.
- **External Tool:** `ffmpeg` terinstal dan terdaftar dalam sistem `PATH` (diperlukan oleh `yt-dlp` untuk encoding MP3 & penyesuaian audio).
- **Python Libraries:**
  - `fastapi` & `uvicorn`: Framework web server backend asinkron berperforma tinggi.
  - `yt-dlp`: Engine pencari dan pengunduh audio YouTube termutakhir.
  - `mutagen`: Engine manipulasi tag ID3 MP3.
  - `requests` / `httpx`: HTTP client untuk ekstraksi web Spotify.
  - `pydantic`: Validasi skema request dan response.

---

### 7. Edge Cases & Error Handling

1. **Invalid URL / Bukan URL Spotify:**
   - Validasi regex format: `^https?://open\.spotify\.com/(track|album|playlist)/[a-zA-Z0-9]+`
   - Kembalikan respon HTTP 400 dengan pesan kesalahan yang jelas.
2. **Audio YouTube Tidak Ditemukan / Region Restricted:**
   - Fallback query pencarian alternatif (misal: `"Judul Lagu - Artis Official"`).
   - Catat track sebagai failed jika tetap tidak ditemukan, tanpa menggugurkan keseluruhan batch playlist.
3. **Karakter Khusus pada Nama File:**
   - Sanitasi nama file output (menghapus karakter ilegal seperti `\ / : * ? " < > |`) agar aman disimpan di filesystem Windows/Linux.
4. **Spotify Rate Limiting:**
   - Caching metadata sederhana di memori untuk URL yang berulang kali diakses dalam waktu singkat.

---

### 8. Implementation Milestones

- **Milestone 1:** Setup struktur project, virtual environment, dan dependensi (`requirements.txt`).
- **Milestone 2:** Implementasi modul ekstraksi metadata Spotify publik (`extractor.py`).
- **Milestone 3:** Implementasi modul pencarian, unduhan, dan tagging MP3 (`downloader.py`, `tagger.py`).
- **Milestone 4:** Implementasi modul batch job & bundling ZIP (`batch.py`).
- **Milestone 5:** Pembuatan FastAPI endpoints & auto-cleaner (`main.py`).
- **Milestone 6:** Pembuatan Web UI modern Spotify Dark Theme (`static/`).
- **Milestone 7:** Pengujian end-to-end (Single track, Album, dan Playlist download).
