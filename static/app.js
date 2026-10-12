// ==========================================================
// SpotiDown — Frontend Application Logic
// ==========================================================

document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const urlForm = document.getElementById("urlForm");
  const spotifyUrlInput = document.getElementById("spotifyUrl");
  const pasteBtn = document.getElementById("pasteBtn");
  const fetchBtn = document.getElementById("fetchBtn");
  const fetchSpinner = document.getElementById("fetchSpinner");
  const formatChips = document.getElementById("formatChips");

  const previewSection = document.getElementById("previewSection");
  const previewCover = document.getElementById("previewCover");
  const previewTypeBadge = document.getElementById("previewTypeBadge");
  const previewYear = document.getElementById("previewYear");
  const previewCountBadge = document.getElementById("previewCountBadge");
  const previewTitle = document.getElementById("previewTitle");
  const previewArtist = document.getElementById("previewArtist");
  const previewAlbum = document.getElementById("previewAlbum");
  const downloadMainBtn = document.getElementById("downloadMainBtn");
  const downloadBtnText = document.getElementById("downloadBtnText");

  const tracklistContainer = document.getElementById("tracklistContainer");
  const trackCountDisplay = document.getElementById("trackCountDisplay");
  const tracklistTbody = document.getElementById("tracklistTbody");
  const downloadAllBtn = document.getElementById("downloadAllBtn");

  const progressModal = document.getElementById("progressModal");
  const closeModalBtn = document.getElementById("closeModalBtn");
  const modalTitle = document.getElementById("modalTitle");
  const modalStatusText = document.getElementById("modalStatusText");
  const modalPercent = document.getElementById("modalPercent");
  const progressBar = document.getElementById("progressBar");
  const modalDetail = document.getElementById("modalDetail");
  const modalFooter = document.getElementById("modalFooter");
  const modalDownloadLink = document.getElementById("modalDownloadLink");

  const toastContainer = document.getElementById("toastContainer");

  // State
  let selectedFormat = "mp3";
  let currentMetadata = null;
  let pollInterval = null;

  // Format Selection
  formatChips.addEventListener("click", (e) => {
    const chip = e.target.closest(".chip");
    if (!chip) return;

    formatChips.querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
    chip.classList.add("active");
    selectedFormat = chip.dataset.format || "mp3";

    updateButtonLabels();
  });

  function updateButtonLabels() {
    const fmtUpper = selectedFormat.toUpperCase();
    if (!currentMetadata) {
      downloadBtnText.textContent = `Unduh ${fmtUpper}`;
      return;
    }

    if (currentMetadata.type === "track") {
      downloadBtnText.textContent = `Unduh ${fmtUpper} (320k)`;
    } else {
      downloadBtnText.textContent = `Unduh Semua ZIP (${fmtUpper})`;
    }

    // Update row buttons
    document.querySelectorAll(".btn-download-row").forEach((btn) => {
      btn.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="7 10 12 15 17 10"></polyline>
          <line x1="12" y1="15" x2="12" y2="3"></line>
        </svg>
        <span>${fmtUpper}</span>
      `;
    });
  }

  // Paste from clipboard
  pasteBtn.addEventListener("click", async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        spotifyUrlInput.value = text.trim();
        showToast("Tautan ditempel dari clipboard!", "success");
      }
    } catch (err) {
      showToast("Gagal membaca clipboard. Tempel manual dengan Ctrl+V.", "error");
    }
  });

  // URL Submit -> Fetch metadata
  urlForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const url = spotifyUrlInput.value.trim();
    if (!url) return;

    setLoading(true);

    try {
      const resp = await fetch("/api/info", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url })
      });

      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.detail || "Gagal mengambil info lagu dari Spotify.");
      }

      currentMetadata = data;
      renderPreview(data);
      showToast("Metadata berhasil dimuat!", "success");
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      setLoading(false);
    }
  });

  function setLoading(isLoading) {
    if (isLoading) {
      fetchBtn.disabled = true;
      fetchSpinner.classList.remove("hidden");
      fetchBtn.querySelector(".btn-text").textContent = "Menganalisa...";
    } else {
      fetchBtn.disabled = false;
      fetchSpinner.classList.add("hidden");
      fetchBtn.querySelector(".btn-text").textContent = "Analisa Link";
    }
  }

  // Render Preview Card & Table
  function renderPreview(data) {
    previewSection.classList.remove("hidden");

    previewCover.src = data.cover_url || "https://placehold.co/300x300/18181c/1db954?text=Spotify";
    previewTypeBadge.textContent = data.type.toUpperCase();
    previewTitle.textContent = data.title;
    previewArtist.textContent = data.artist_display || data.artists?.join(", ") || "";
    previewAlbum.textContent = data.album || (data.type === "track" ? data.tracks?.[0]?.album : "") || "";

    const year = data.year || data.tracks?.[0]?.year || "";
    if (year) {
      previewYear.textContent = year;
      previewYear.classList.remove("hidden");
    } else {
      previewYear.classList.add("hidden");
    }

    if (data.total_tracks > 1) {
      previewCountBadge.textContent = `${data.total_tracks} Lagu`;
      previewCountBadge.classList.remove("hidden");
    } else {
      previewCountBadge.classList.add("hidden");
    }

    updateButtonLabels();

    // Table for playlist / album
    if (data.type !== "track" && data.tracks && data.tracks.length > 0) {
      tracklistContainer.classList.remove("hidden");
      trackCountDisplay.textContent = data.tracks.length;
      renderTracklistTable(data.tracks);
    } else {
      tracklistContainer.classList.add("hidden");
    }

    // Smooth scroll into preview
    previewSection.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function renderTracklistTable(tracks) {
    tracklistTbody.innerHTML = "";
    tracks.forEach((track, index) => {
      const tr = document.createElement("tr");

      const durationStr = formatDuration(track.duration_sec);
      const trackThumb = track.cover_url || currentMetadata.cover_url || "";

      tr.innerHTML = `
        <td style="color: var(--text-sub); font-weight: 600;">${index + 1}</td>
        <td>
          <div class="track-cell-title">
            ${trackThumb ? `<img src="${trackThumb}" class="track-thumb" alt="cover">` : ''}
            <div class="track-meta-wrap">
              <span class="track-name">${escapeHtml(track.title)}</span>
              <span class="track-sub">${escapeHtml(track.artist_display || "")}</span>
            </div>
          </div>
        </td>
        <td style="color: var(--text-sub);">${durationStr}</td>
        <td style="text-align: right;">
          <button class="btn-download-row" data-index="${index}">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
            <span>${selectedFormat.toUpperCase()}</span>
          </button>
        </td>
      `;

      tr.querySelector(".btn-download-row").addEventListener("click", () => {
        downloadSingleTrack(track);
      });

      tracklistTbody.appendChild(tr);
    });
  }

  // Main Download Button Click
  downloadMainBtn.addEventListener("click", () => {
    if (!currentMetadata) return;

    if (currentMetadata.type === "track") {
      const track = currentMetadata.tracks[0];
      downloadSingleTrack(track);
    } else {
      downloadBatch();
    }
  });

  downloadAllBtn.addEventListener("click", () => {
    downloadBatch();
  });

  // Action: Download Single Track
  async function downloadSingleTrack(track) {
    openModal("Mengunduh Lagu...", "Mencari audio stream di YouTube...");
    progressBar.style.width = "25%";
    modalPercent.textContent = "25%";
    modalDetail.textContent = `${track.artist_display} - ${track.title} [${selectedFormat.toUpperCase()}]`;

    try {
      const resp = await fetch("/api/download/track", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          track: track,
          format: selectedFormat
        })
      });

      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.detail || "Gagal mengunduh lagu.");
      }

      progressBar.style.width = "100%";
      modalPercent.textContent = "100%";
      modalStatusText.textContent = "Selesai! Unduhan Anda siap.";
      modalDetail.textContent = `File: ${data.filename}`;

      showDownloadLink(data.download_url, data.filename);
      triggerAutoDownload(data.download_url, data.filename);
    } catch (err) {
      modalStatusText.textContent = "Gagal Mengunduh";
      modalDetail.textContent = err.message;
      progressBar.style.background = "#eb5757";
      showToast(err.message, "error");
    }
  }

  // Action: Download Batch (Album/Playlist)
  async function downloadBatch() {
    if (!currentMetadata || !currentMetadata.tracks?.length) return;

    openModal(`Mengunduh ${currentMetadata.type.toUpperCase()}`, "Menyiapkan antrean unduhan...");
    progressBar.style.width = "5%";
    modalPercent.textContent = "5%";
    modalDetail.textContent = `Total: ${currentMetadata.tracks.length} lagu [${selectedFormat.toUpperCase()}]`;

    try {
      const resp = await fetch("/api/download/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: currentMetadata.title,
          tracks: currentMetadata.tracks,
          format: selectedFormat
        })
      });

      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.detail || "Gagal memulai unduhan batch.");
      }

      const taskId = data.task_id;
      startPollingProgress(taskId);
    } catch (err) {
      modalStatusText.textContent = "Gagal Memproses Batch";
      modalDetail.textContent = err.message;
      progressBar.style.background = "#eb5757";
      showToast(err.message, "error");
    }
  }

  // Polling Batch Progress
  function startPollingProgress(taskId) {
    if (pollInterval) clearInterval(pollInterval);

    pollInterval = setInterval(async () => {
      try {
        const resp = await fetch(`/api/progress/${taskId}`);
        if (!resp.ok) return;

        const progress = await resp.json();
        const percent = Math.round((progress.completed_tracks / (progress.total_tracks || 1)) * 90);

        if (progress.status === "downloading") {
          progressBar.style.width = `${Math.max(10, percent)}%`;
          modalPercent.textContent = `${Math.max(10, percent)}%`;
          modalStatusText.textContent = `Mengunduh (${progress.completed_tracks}/${progress.total_tracks})...`;
          modalDetail.textContent = progress.current_song || "Memproses lagu...";
        } else if (progress.status === "packaging") {
          progressBar.style.width = "95%";
          modalPercent.textContent = "95%";
          modalStatusText.textContent = "Mengemas file ke arsip ZIP...";
          modalDetail.textContent = "Hampir selesai...";
        } else if (progress.status === "completed") {
          clearInterval(pollInterval);
          progressBar.style.width = "100%";
          modalPercent.textContent = "100%";
          modalStatusText.textContent = "Selesai! File ZIP siap diunduh.";
          modalDetail.textContent = `Arsip: ${progress.zip_filename}`;

          showDownloadLink(progress.download_url, progress.zip_filename);
          triggerAutoDownload(progress.download_url, progress.zip_filename);
        } else if (progress.status === "failed") {
          clearInterval(pollInterval);
          modalStatusText.textContent = "Gagal Mengunduh Batch";
          modalDetail.textContent = progress.error || "Terjadi kesalahan internal.";
          progressBar.style.background = "#eb5757";
        }
      } catch (err) {
        console.error("Polling error:", err);
      }
    }, 1500);
  }

  // Modal UI Helpers
  function openModal(title, initialStatus) {
    modalTitle.textContent = title;
    modalStatusText.textContent = initialStatus;
    modalPercent.textContent = "0%";
    progressBar.style.width = "0%";
    progressBar.style.background = "linear-gradient(90deg, #1db954, #1ed760, #4ae587)";
    modalFooter.classList.add("hidden");
    progressModal.classList.remove("hidden");
  }

  function showDownloadLink(url, filename) {
    modalDownloadLink.href = url;
    modalDownloadLink.download = filename;
    modalFooter.classList.remove("hidden");
  }

  function triggerAutoDownload(url, filename) {
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    showToast(`Unduhan ${filename} dimulai otomatis!`, "success");
  }

  closeModalBtn.addEventListener("click", () => {
    if (pollInterval) clearInterval(pollInterval);
    progressModal.classList.add("hidden");
  });

  progressModal.addEventListener("click", (e) => {
    if (e.target === progressModal) {
      if (pollInterval) clearInterval(pollInterval);
      progressModal.classList.add("hidden");
    }
  });

  // Utilities
  function formatDuration(sec) {
    if (!sec || isNaN(sec)) return "--:--";
    const mins = Math.floor(sec / 60);
    const secs = Math.floor(sec % 60);
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  }

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function showToast(message, type = "success") {
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.innerHTML = `
      <span>${type === "success" ? "✓" : "⚠️"}</span>
      <span>${escapeHtml(message)}</span>
    `;
    toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(40px)";
      toast.style.transition = "all 0.3s";
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }
});
