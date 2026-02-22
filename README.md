# XFeat Vision Lab 🚀

**AI-powered object matching in videos using XFeat (CVPR 2024)**

Upload any object photo + video. XFeat will locate, count, or replace the object — frame by frame.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔍 **Find Object** | Uploads object photo + video → returns the exact **timestamp** where the object best appears |
| 🔢 **Count Appearances** | Counts how many times the object **shows then disappears** in the video |
| 🎭 **Replace Object** | Replaces the object in every frame with your own image → outputs a new video |

---

## 🗂️ Project Structure

```
xfeat-webapp/
├── backend/
│   ├── app.py              # Flask REST API (3 endpoints)
│   ├── xfeat_engine.py     # Core XFeat logic for all 3 features
│   ├── requirements.txt    # Python dependencies
│   ├── uploads/            # Temp uploaded files
│   ├── outputs/            # Generated output videos
│   └── accelerated_features/  # XFeat repo (auto-cloned by setup.ps1)
├── frontend/
│   ├── index.html          # Single-page app
│   ├── style.css           # Premium dark-mode design
│   └── app.js              # Tab logic, API calls, charts
├── setup.ps1               # Run once to install everything
└── start.ps1               # Run every time to launch
```

---

## 🚀 Quick Start

### Step 1 — Run setup (once only)

Open PowerShell in the `xfeat-webapp` folder:

```powershell
.\setup.ps1
```

This will:
- Clone the XFeat repo from GitHub
- Install all Python packages (Flask, PyTorch, OpenCV, etc.)

> ⏱️ First-time setup takes ~5–10 min (PyTorch download)

### Step 2 — Start the app

```powershell
.\start.ps1
```

This starts the Flask backend at **http://localhost:5000** and opens the web UI automatically.

---

## 🔧 Manual Start (if needed)

```powershell
# Terminal 1 — start backend
cd backend
python app.py

# Then open frontend/index.html in your browser
```

---

## 📋 Requirements

- **Python 3.8+** (`python --version`)
- **git** (`git --version`)
- **pip** (comes with Python)

> GPU (CUDA) is automatically used if available — much faster for long videos.

---

## 💡 Tips

- **Feature 1**: Works best with clear, well-lit object photos
- **Feature 2**: Set `high_thresh` higher if getting false positives (edit `xfeat_engine.py`)
- **Feature 3**: Best results with **planar objects** (book covers, logos, screens, posters)
- For **GPU acceleration**: install `torch` with CUDA support from [pytorch.org](https://pytorch.org)

---

## 📌 Based On

- [XFeat: Accelerated Features for Lightweight Image Matching — CVPR 2024](https://arxiv.org/abs/2404.19174)
- [verlab/accelerated_features](https://github.com/verlab/accelerated_features)
