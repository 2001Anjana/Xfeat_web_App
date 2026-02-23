/* ═══════════════════════════════════════════════════
   XFeat Vision Lab — Frontend JavaScript
   Handles: tab switching, drag-and-drop, API calls,
            job polling, Chart.js rendering, results
   ═══════════════════════════════════════════════════ */

// ─── API Configuration ────────────────────────────
// For local development: leave AZURE_URL as empty string ""
// For Azure deployment:  set AZURE_URL to your App Service URL
const AZURE_URL = "https://xfeat-webapp-cnaccchvadfmgbgk.southindia-01.azurewebsites.net";

const API = (AZURE_URL || "http://localhost:5000") + "/api";


// ─── Tab switching ────────────────────────────────
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    const tab = btn.dataset.tab;
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`panel-${tab}`).classList.add("active");
  });
});

// ─── Drop Zone: file change + drag-and-drop ──────

function setupDropZone(dzId, inputId, previewId, accept) {
  const dz = document.getElementById(dzId);
  const input = document.getElementById(inputId);
  const prev = document.getElementById(previewId);

  // Native file picker fires via <label for="..."> — no JS click needed.
  // Just listen to the change event.
  input.addEventListener("change", () => {
    if (input.files[0]) handleFile(input.files[0], dz, prev, accept);
  });

  // Drag-and-drop support
  ["dragenter", "dragover"].forEach(ev =>
    dz.addEventListener(ev, e => { e.preventDefault(); dz.classList.add("dragover"); })
  );
  ["dragleave", "drop"].forEach(ev =>
    dz.addEventListener(ev, e => { e.preventDefault(); dz.classList.remove("dragover"); })
  );
  dz.addEventListener("drop", e => {
    const file = e.dataTransfer.files[0];
    if (!file) return;
    // Assign to input so FormData picks it up later
    const dt = new DataTransfer();
    dt.items.add(file);
    input.files = dt.files;
    handleFile(file, dz, prev, accept);
  });
}

function handleFile(file, dz, previewEl, accept) {
  dz.classList.add("has-file");
  previewEl.innerHTML = "";

  const nameDiv = document.createElement("div");
  nameDiv.className = "preview-name";
  nameDiv.textContent = file.name;

  if (accept === "image") {
    const img = document.createElement("img");
    img.src = URL.createObjectURL(file);
    previewEl.appendChild(img);
  } else {
    const vid = document.createElement("video");
    vid.src = URL.createObjectURL(file);
    vid.muted = true;
    vid.loop = true;
    vid.autoplay = true;
    previewEl.appendChild(vid);
  }
  previewEl.appendChild(nameDiv);
}

// Wire all drop zones
setupDropZone("dz-find-img", "inp-find-img", "prev-find-img", "image");
setupDropZone("dz-find-vid", "inp-find-vid", "prev-find-vid", "video");
setupDropZone("dz-count-img", "inp-count-img", "prev-count-img", "image");
setupDropZone("dz-count-vid", "inp-count-vid", "prev-count-vid", "video");
setupDropZone("dz-repl-img", "inp-repl-img", "prev-repl-img", "image");
setupDropZone("dz-repl-sub", "inp-repl-sub", "prev-repl-sub", "image");
setupDropZone("dz-repl-vid", "inp-repl-vid", "prev-repl-vid", "video");

// ─── Job polling ──────────────────────────────────

function pollJob(jobId, onProgress, onDone, onError) {
  const interval = setInterval(async () => {
    try {
      const res = await fetch(`${API}/status/${jobId}`);
      const data = await res.json();

      if (data.status === "running") {
        onProgress(data.progress || 0);
      } else if (data.status === "done") {
        clearInterval(interval);
        onProgress(100);
        onDone(data.result);
      } else if (data.status === "error") {
        clearInterval(interval);
        onError(data.result?.error || "Unknown error");
      }
    } catch (e) {
      clearInterval(interval);
      onError("Cannot reach backend. Is the server running?");
    }
  }, 1200);
}

function setProgress(prefix, pct) {
  document.getElementById(`pbar-${prefix}`).style.width = pct + "%";
  document.getElementById(`ppct-${prefix}`).textContent = pct + "%";
}

function showError(msg) {
  alert("❌ Error: " + msg);
}

// ─── Chart helper ─────────────────────────────────
const _charts = {};

function renderChart(canvasId, stats, appearances) {
  const ctx = document.getElementById(canvasId).getContext("2d");
  if (_charts[canvasId]) _charts[canvasId].destroy();

  const labels = stats.map(s => s.time.toFixed(1) + "s");
  const matches = stats.map(s => s.matches);

  const datasets = [{
    label: "Match score",
    data: matches,
    borderColor: "#7c6bff",
    backgroundColor: "rgba(124,107,255,0.12)",
    fill: true,
    tension: 0.35,
    pointRadius: 0,
    borderWidth: 2,
  }];

  // Mark appearance windows (Feature 2)
  if (appearances && appearances.length > 0) {
    appearances.forEach((ap, i) => {
      datasets.push({
        label: `Appearance ${i + 1}`,
        data: stats.map(s =>
          s.time >= ap.start_time && s.time <= ap.end_time ? ap.peak_matches : null
        ),
        borderColor: "#00f5a0",
        backgroundColor: "rgba(0,245,160,0.08)",
        fill: true,
        tension: 0.2,
        pointRadius: 0,
        borderWidth: 1.5,
        borderDash: [4, 3],
      });
    });
  }

  _charts[canvasId] = new Chart(ctx, {
    type: "line",
    data: { labels, datasets },
    options: {
      responsive: true,
      plugins: {
        legend: { labels: { color: "#8892b0", font: { family: "Inter", size: 11 } } },
        tooltip: {
          backgroundColor: "rgba(14,18,40,0.92)",
          borderColor: "#7c6bff",
          borderWidth: 1,
          titleColor: "#e8eaf6",
          bodyColor: "#8892b0",
        }
      },
      scales: {
        x: { ticks: { color: "#4a5568", maxTicksLimit: 12, font: { size: 10 } }, grid: { color: "rgba(255,255,255,0.04)" } },
        y: { ticks: { color: "#4a5568", font: { size: 10 } }, grid: { color: "rgba(255,255,255,0.04)" }, beginAtZero: true }
      }
    }
  });
}

// ─── FEATURE 1: Find Object ───────────────────────

document.getElementById("btn-find").addEventListener("click", async () => {
  const img = document.getElementById("inp-find-img").files[0];
  const vid = document.getElementById("inp-find-vid").files[0];
  if (!img || !vid) { alert("Please upload both an object image and a video."); return; }

  const btn = document.getElementById("btn-find");
  btn.disabled = true;

  const prog = document.getElementById("prog-find");
  const res = document.getElementById("result-find");
  prog.classList.remove("hidden");
  res.classList.add("hidden");
  setProgress("find", 0);

  const form = new FormData();
  form.append("query_image", img);
  form.append("video", vid);

  try {
    const r = await fetch(`${API}/find-object`, { method: "POST", body: form });
    const data = await r.json();
    if (data.error) { showError(data.error); btn.disabled = false; return; }

    const jobId = data.job_id;
    pollJob(jobId,
      pct => setProgress("find", pct),
      result => {
        btn.disabled = false;
        prog.classList.add("hidden");
        renderFindResult(result);
      },
      err => { btn.disabled = false; showError(err); }
    );
  } catch (e) {
    btn.disabled = false;
    showError(`Cannot reach backend at: ${API}`);
  }
});

function renderFindResult(r) {
  const card = document.getElementById("result-find");
  card.classList.remove("hidden");

  const statusEl = document.getElementById("res-find-status");
  if (r.confirmed) {
    statusEl.className = "result-status success";
    statusEl.textContent = "✅ Object Found in Video!";
  } else {
    statusEl.className = "result-status warning";
    statusEl.textContent = "⚠️ Object Not Found (too few matches)";
  }

  // Stats chips
  const statsEl = document.getElementById("res-find-stats");
  const ts = r.best_timestamp;
  const mins = Math.floor(ts / 60).toString().padStart(2, "0");
  const secs = (ts % 60).toFixed(2).padStart(5, "0");

  statsEl.innerHTML = `
    <div class="stat-chip"><div class="sc-value">${mins}:${secs}</div><div class="sc-label">Best Timestamp</div></div>
    <div class="stat-chip"><div class="sc-value">${r.best_matches}</div><div class="sc-label">Match Score</div></div>
    <div class="stat-chip"><div class="sc-value">Frame ${r.best_frame}</div><div class="sc-label">Best Frame</div></div>
    <div class="stat-chip"><div class="sc-value">${r.total_frames_checked}</div><div class="sc-label">Frames Checked</div></div>
  `;

  // Preview image
  if (r.preview_b64) {
    const imgEl = document.getElementById("res-find-img");
    imgEl.src = "data:image/png;base64," + r.preview_b64;
    imgEl.style.display = "block";
    document.querySelector(".result-preview-wrap").style.display = "block";
  }

  // Top 5 timestamps
  const topEl = document.getElementById("res-find-top");
  topEl.innerHTML = "<div class='result-label'>Top Matching Moments</div>";
  (r.top_timestamps || []).forEach((t, i) => {
    const m = Math.floor(t.time / 60).toString().padStart(2, "0");
    const s = (t.time % 60).toFixed(2).padStart(5, "0");
    topEl.innerHTML += `
      <div class="ts-row">
        <span class="ts-rank">#${i + 1}</span>
        <span class="ts-time">${m}:${s}</span>
        <span class="ts-matches">${t.matches} matches</span>
      </div>`;
  });

  // Chart
  if (r.stats && r.stats.length > 0) {
    renderChart("chart-find", r.stats, null);
  }
}

// ─── FEATURE 2: Count Appearances ────────────────

document.getElementById("btn-count").addEventListener("click", async () => {
  const img = document.getElementById("inp-count-img").files[0];
  const vid = document.getElementById("inp-count-vid").files[0];
  if (!img || !vid) { alert("Please upload both an object image and a video."); return; }

  const btn = document.getElementById("btn-count");
  btn.disabled = true;

  const prog = document.getElementById("prog-count");
  const res = document.getElementById("result-count");
  prog.classList.remove("hidden");
  res.classList.add("hidden");
  setProgress("count", 0);

  const form = new FormData();
  form.append("query_image", img);
  form.append("video", vid);

  try {
    const r = await fetch(`${API}/count-object`, { method: "POST", body: form });
    const data = await r.json();
    if (data.error) { showError(data.error); btn.disabled = false; return; }

    pollJob(data.job_id,
      pct => setProgress("count", pct),
      result => {
        btn.disabled = false;
        prog.classList.add("hidden");
        renderCountResult(result);
      },
      err => { btn.disabled = false; showError(err); }
    );
  } catch (e) {
    btn.disabled = false;
    showError("Cannot reach backend. Is the server running at localhost:5000?");
  }
});

function renderCountResult(r) {
  const card = document.getElementById("result-count");
  card.classList.remove("hidden");

  // Big number (animate count-up)
  const numEl = document.getElementById("res-count-number");
  let cur = 0;
  const target = r.count || 0;
  const step = Math.max(1, Math.ceil(target / 30));
  const t = setInterval(() => {
    cur = Math.min(cur + step, target);
    numEl.textContent = cur;
    if (cur >= target) clearInterval(t);
  }, 40);

  // Appearances list
  const listEl = document.getElementById("res-appearances");
  listEl.innerHTML = "";
  if (!r.appearances || r.appearances.length === 0) {
    listEl.innerHTML = "<p style='color:var(--text-muted);padding:0 24px'>No appearances detected. Try adjusting the match threshold.</p>";
  } else {
    r.appearances.forEach((ap, i) => {
      const dur = ((ap.end_time || 0) - ap.start_time).toFixed(1);
      listEl.innerHTML += `
        <div class="app-row">
          <div class="app-num">${i + 1}</div>
          <div class="app-range">
            <strong>${ap.start_time.toFixed(2)}s → ${(ap.end_time || 0).toFixed(2)}s</strong>
            <span>Duration: ${dur}s</span>
          </div>
          <div class="app-peak">
            <strong>${ap.peak_matches} matches</strong>
            <span>peak at ${ap.peak_time.toFixed(2)}s</span>
          </div>
        </div>`;
    });
  }

  // Chart with appearance bands
  if (r.stats && r.stats.length > 0) {
    renderChart("chart-count", r.stats, r.appearances);
  }
}

// ─── FEATURE 3: Replace Object ───────────────────

document.getElementById("btn-replace").addEventListener("click", async () => {
  const img = document.getElementById("inp-repl-img").files[0];
  const sub = document.getElementById("inp-repl-sub").files[0];
  const vid = document.getElementById("inp-repl-vid").files[0];
  if (!img || !sub || !vid) { alert("Please upload the object photo, a replacement image, and a video."); return; }

  const btn = document.getElementById("btn-replace");
  btn.disabled = true;

  const prog = document.getElementById("prog-replace");
  const res = document.getElementById("result-replace");
  prog.classList.remove("hidden");
  res.classList.add("hidden");
  setProgress("replace", 0);

  const form = new FormData();
  form.append("query_image", img);
  form.append("replacement_image", sub);
  form.append("video", vid);

  try {
    const r = await fetch(`${API}/replace-object`, { method: "POST", body: form });
    const data = await r.json();
    if (data.error) { showError(data.error); btn.disabled = false; return; }

    pollJob(data.job_id,
      pct => setProgress("replace", pct),
      result => {
        btn.disabled = false;
        prog.classList.add("hidden");
        renderReplaceResult(result, data.job_id);
      },
      err => { btn.disabled = false; showError(err); }
    );
  } catch (e) {
    btn.disabled = false;
    showError(`Cannot reach backend at: ${API}`);
  }
});

function renderReplaceResult(r, jobId) {
  const card = document.getElementById("result-replace");
  card.classList.remove("hidden");

  const statsEl = document.getElementById("res-replace-stats");
  const pct = r.total_frames > 0 ? Math.round((r.frames_replaced / r.total_frames) * 100) : 0;
  statsEl.innerHTML = `
    <div class="stat-chip"><div class="sc-value">${r.frames_replaced}</div><div class="sc-label">Frames Replaced</div></div>
    <div class="stat-chip"><div class="sc-value">${r.total_frames}</div><div class="sc-label">Total Frames</div></div>
    <div class="stat-chip"><div class="sc-value">${pct}%</div><div class="sc-label">Coverage</div></div>
    <div class="stat-chip"><div class="sc-value">${(r.fps || 0).toFixed(1)}</div><div class="sc-label">FPS</div></div>
  `;

  // Get the output filename from path
  const pathParts = (r.output_path || "").replace(/\\/g, "/").split("/");
  const filename = pathParts[pathParts.length - 1];
  const videoUrl = `${API}/video/${filename}`;

  // Set video player src
  const videoEl = document.getElementById("res-replace-video");
  videoEl.src = videoUrl;
  videoEl.load();

  // Fix download button: use fetch → blob → click to bypass cross-origin restriction
  const dlBtn = document.getElementById("res-replace-dl");
  dlBtn.onclick = async (e) => {
    e.preventDefault();
    dlBtn.textContent = "⏳ Preparing download...";
    dlBtn.disabled = true;
    try {
      const resp = await fetch(videoUrl);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const blob = await resp.blob();
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(blobUrl), 5000);
    } catch (err) {
      alert("Download failed: " + err.message);
    } finally {
      dlBtn.textContent = "⬇ Download Generated Video";
      dlBtn.disabled = false;
    }
  };
}

