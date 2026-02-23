# -*- coding: utf-8 -*-
"""
app.py  —  XFeat Web Application Flask Backend
Endpoints:
  POST /api/find-object       → Feature 1: Locate object in video
  POST /api/count-object      → Feature 2: Count appearances
  POST /api/replace-object    → Feature 3: AR replacement video
  GET  /api/status/<job_id>   → Poll job progress
  GET  /api/video/<filename>  → Serve output video
"""

import os
import uuid
import threading
from pathlib import Path
from flask import Flask, request, jsonify, send_file, abort
from flask_cors import CORS
from werkzeug.utils import secure_filename

import xfeat_engine as engine

# ─── App Config ──────────────────────────────
BASE_DIR   = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

ALLOWED_IMG = {"png", "jpg", "jpeg", "bmp", "webp"}
ALLOWED_VID = {"mp4", "avi", "mov", "mkv", "webm"}
MAX_CONTENT_MB = 500

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_MB * 1024 * 1024
CORS(app)

# ─── In-memory job store ──────────────────────
# jobs[job_id] = { "status": "running"|"done"|"error",
#                  "progress": 0-100, "result": {...} }
jobs: dict = {}


def _allowed(filename, allowed_set):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_set


def _save_upload(file_obj, allowed_set, prefix=""):
    if not file_obj or file_obj.filename == "":
        return None, "No file provided."
    if not _allowed(file_obj.filename, allowed_set):
        return None, f"File type not allowed. Allowed: {allowed_set}"
    fname = prefix + "_" + secure_filename(file_obj.filename)
    path  = UPLOAD_DIR / fname
    file_obj.save(str(path))
    return str(path), None


def _run_job(job_id: str, fn, *args, **kwargs):
    """Execute a job in a background thread, updating jobs dict."""
    def progress_cb(pct):
        jobs[job_id]["progress"] = pct

    jobs[job_id] = {"status": "running", "progress": 0, "result": None}
    try:
        result = fn(*args, progress_cb=progress_cb, **kwargs)
        if "error" in result:
            jobs[job_id] = {"status": "error", "progress": 100, "result": result}
        else:
            jobs[job_id] = {"status": "done", "progress": 100, "result": result}
    except Exception as e:
        jobs[job_id] = {"status": "error", "progress": 100,
                        "result": {"error": str(e)}}


# ─── Status endpoint ──────────────────────────
@app.route("/api/status/<job_id>", methods=["GET"])
def get_status(job_id):
    job = jobs.get(job_id)
    if job is None:
        return jsonify({"error": "Unknown job ID"}), 404
    return jsonify(job)


# ─── Feature 1: Find Object ───────────────────
@app.route("/api/find-object", methods=["POST"])
def api_find_object():
    query_file = request.files.get("query_image")
    video_file = request.files.get("video")
    job_id = str(uuid.uuid4())

    query_path, err = _save_upload(query_file, ALLOWED_IMG, job_id + "_q")
    if err:
        return jsonify({"error": f"Query image: {err}"}), 400

    video_path, err = _save_upload(video_file, ALLOWED_VID, job_id + "_v")
    if err:
        return jsonify({"error": f"Video: {err}"}), 400

    t = threading.Thread(
        target=_run_job,
        args=(job_id, engine.find_object_in_video, query_path, video_path),
        daemon=True
    )
    t.start()
    return jsonify({"job_id": job_id}), 202


# ─── Feature 2: Count Appearances ────────────
@app.route("/api/count-object", methods=["POST"])
def api_count_object():
    query_file = request.files.get("query_image")
    video_file = request.files.get("video")
    job_id = str(uuid.uuid4())

    query_path, err = _save_upload(query_file, ALLOWED_IMG, job_id + "_q")
    if err:
        return jsonify({"error": f"Query image: {err}"}), 400

    video_path, err = _save_upload(video_file, ALLOWED_VID, job_id + "_v")
    if err:
        return jsonify({"error": f"Video: {err}"}), 400

    t = threading.Thread(
        target=_run_job,
        args=(job_id, engine.count_object_appearances, query_path, video_path),
        daemon=True
    )
    t.start()
    return jsonify({"job_id": job_id}), 202


# ─── Feature 3: Replace Object ────────────────
@app.route("/api/replace-object", methods=["POST"])
def api_replace_object():
    query_file   = request.files.get("query_image")
    video_file   = request.files.get("video")
    replace_file = request.files.get("replacement_image")
    job_id = str(uuid.uuid4())

    query_path, err = _save_upload(query_file, ALLOWED_IMG, job_id + "_q")
    if err:
        return jsonify({"error": f"Query image: {err}"}), 400

    video_path, err = _save_upload(video_file, ALLOWED_VID, job_id + "_v")
    if err:
        return jsonify({"error": f"Video: {err}"}), 400

    repl_path, err = _save_upload(replace_file, ALLOWED_IMG, job_id + "_r")
    if err:
        return jsonify({"error": f"Replacement image: {err}"}), 400

    output_path = str(OUTPUT_DIR / f"{job_id}_output.mp4")

    t = threading.Thread(
        target=_run_job,
        args=(job_id, engine.replace_object_in_video,
              query_path, video_path, repl_path, output_path),
        daemon=True
    )
    t.start()
    return jsonify({"job_id": job_id}), 202


# ─── Serve output video ───────────────────────
@app.route("/api/video/<filename>", methods=["GET"])
def serve_video(filename):
    path = OUTPUT_DIR / secure_filename(filename)
    if not path.exists():
        abort(404)
    return send_file(str(path), mimetype="video/mp4",
                     as_attachment=False)


# ─── Health check ────────────────────────────
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "XFeat backend is running."})


if __name__ == "__main__":
    print("=" * 50)
    print("  XFeat Object Matching — Backend Server")
    print("  http://localhost:5000")
    print("=" * 50)
    # Pre-load model at startup
    engine.get_model()
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
