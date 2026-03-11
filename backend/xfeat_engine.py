# -*- coding: utf-8 -*-
"""
xfeat_engine.py
Core XFeat processing logic for all 3 features.
"""

import os
import sys
import cv2
import numpy as np
import torch
import base64
import json
import subprocess
import shutil
from io import BytesIO
from PIL import Image
from pathlib import Path

# ─────────────────────────────────────────────
# XFeat path setup (cloned repo inside backend/)
# ─────────────────────────────────────────────
XFEAT_PATH = Path(__file__).parent / "accelerated_features"
if str(XFEAT_PATH) not in sys.path:
    sys.path.insert(0, str(XFEAT_PATH))

_xfeat_model = None
_device = None


def get_model():
    """Lazy-load XFeat model (singleton)."""
    global _xfeat_model, _device
    if _xfeat_model is None:
        from modules.xfeat import XFeat
        _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        _xfeat_model = XFeat()
        print(f"[XFeat] Model loaded on {_device}")
    return _xfeat_model, _device


# ─────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────

def preprocess_image(image, max_size=640):
    h, w = image.shape[:2]
    scale = min(max_size / max(h, w), 1.0)
    new_h = ((int(h * scale)) // 8) * 8
    new_w = ((int(w * scale)) // 8) * 8
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    return resized, scale


def image_to_tensor(image, device):
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    tensor = torch.from_numpy(rgb).permute(2, 0, 1).float() / 255.0
    return tensor.unsqueeze(0).to(device)


def extract_features(image, xfeat_model, device, max_size=640):
    proc, scale = preprocess_image(image, max_size)
    tensor = image_to_tensor(proc, device)
    with torch.no_grad():
        out = xfeat_model.detectAndCompute(tensor, top_k=4096)[0]
    return out["keypoints"], out["descriptors"], scale, proc


def match_descriptors(xfeat_model, desc1, desc2, threshold=0.82):
    with torch.no_grad():
        idx0, idx1 = xfeat_model.match(desc1, desc2, threshold)
    return idx0, idx1


def img_to_b64(img_bgr):
    """Convert OpenCV BGR image to base64 PNG string for JSON transport."""
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(rgb)
    buf = BytesIO()
    pil.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def draw_keypoints(image, kp_tensor, color=(0, 255, 80), max_kp=500):
    out = image.copy()
    kp = kp_tensor.cpu().numpy()[:max_kp]
    for pt in kp:
        cv2.circle(out, tuple(map(int, pt)), 3, color, -1, cv2.LINE_AA)
    return out


def draw_matches_side_by_side(img1, kp1, img2, kp2, idx0, idx1, max_draw=80):
    h1, w1 = img1.shape[:2]
    h2, w2 = img2.shape[:2]
    h = max(h1, h2)
    canvas = np.zeros((h, w1 + w2, 3), dtype=np.uint8)
    canvas[:h1, :w1] = img1
    canvas[:h2, w1:] = img2

    kp1_np = kp1[idx0].cpu().numpy()
    kp2_np = kp2[idx1].cpu().numpy()

    step = max(1, len(kp1_np) // max_draw)
    for i in range(0, len(kp1_np), step):
        pt1 = tuple(map(int, kp1_np[i]))
        pt2 = (int(kp2_np[i][0]) + w1, int(kp2_np[i][1]))
        color = (0, 200, 0)
        cv2.line(canvas, pt1, pt2, color, 1, cv2.LINE_AA)
        cv2.circle(canvas, pt1, 3, color, -1, cv2.LINE_AA)
        cv2.circle(canvas, pt2, 3, color, -1, cv2.LINE_AA)
    return canvas


# ─────────────────────────────────────────────
# FEATURE 1 — Find Object in Video
# Returns: best frame timestamp and match image
# ─────────────────────────────────────────────

def find_object_in_video(query_path: str, video_path: str,
                         frame_skip_factor: int = 5,
                         match_threshold: float = 0.82,
                         min_matches: int = 8,
                         progress_cb=None) -> dict:
    """
    Scan every N-th frame of the video and find the frame
    with the highest XFeat match count against the query image.
    Returns best frame timestamp, match count, and preview image.
    """
    xfeat, device = get_model()

    query_img = cv2.imread(query_path)
    if query_img is None:
        return {"error": "Cannot read query image."}

    ref_kp, ref_desc, _, ref_proc = extract_features(query_img, xfeat, device)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {"error": "Cannot open video."}

    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_skip = max(1, int(fps // frame_skip_factor))

    best = {"matches": 0, "frame_idx": 0, "timestamp": 0.0, "img": None}
    all_stats = []
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_skip == 0:
            curr_kp, curr_desc, _, curr_proc = extract_features(frame, xfeat, device)
            idx0, idx1 = match_descriptors(xfeat, ref_desc, curr_desc, match_threshold)
            n = len(idx0)

            ts = frame_idx / fps
            all_stats.append({"frame": frame_idx, "time": round(ts, 2), "matches": n})

            if n > best["matches"]:
                # Build side-by-side preview for the best frame
                preview = draw_matches_side_by_side(ref_proc, ref_kp, curr_proc, curr_kp, idx0, idx1)
                best = {"matches": n, "frame_idx": frame_idx,
                        "timestamp": round(ts, 2), "img": preview}

            if progress_cb and total > 0:
                progress_cb(int(frame_idx / total * 100))

        frame_idx += 1

    cap.release()

    confirmed = best["matches"] >= min_matches
    result = {
        "confirmed": confirmed,
        "best_timestamp": best["timestamp"],
        "best_frame": best["frame_idx"],
        "best_matches": best["matches"],
        "total_frames_checked": len(all_stats),
        "fps": fps,
        "stats": all_stats,
    }
    if best["img"] is not None:
        result["preview_b64"] = img_to_b64(best["img"])

    # Top 5 timestamps
    top5 = sorted(all_stats, key=lambda x: x["matches"], reverse=True)[:5]
    result["top_timestamps"] = top5

    return result


# ─────────────────────────────────────────────
# FEATURE 2 — Count Object Appearances
# State-machine: NOT_VISIBLE ↔ VISIBLE
# ─────────────────────────────────────────────

def count_object_appearances(query_path: str, video_path: str,
                              frame_skip_factor: int = 5,
                              match_threshold: float = 0.80,
                              smoothing_window: int = 3,
                              high_ratio: float = 0.5,
                              low_ratio: float = -0.3,
                              min_gap_sec: float = 0.5,
                              min_duration_sec: float = 0.2,
                              progress_cb=None) -> dict:
    """
    Count how many discrete times the object appears (then disappears) in the video.

    Uses adaptive thresholds derived from the actual score distribution:
      high_thresh = mean + high_ratio * std   (enter VISIBLE)
      low_thresh  = mean + low_ratio  * std   (exit VISIBLE)

    Scores are smoothed with a rolling average before threshold comparison.
    min_gap_sec enforces a minimum gap between appearances to avoid
    micro-oscillations splitting one appearance into many.
    min_duration_sec ensures brief spurious detections are ignored.
    """
    xfeat, device = get_model()

    query_img = cv2.imread(query_path)
    if query_img is None:
        return {"error": "Cannot read query image."}

    ref_kp, ref_desc, _, _ = extract_features(query_img, xfeat, device)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {"error": "Cannot open video."}

    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_skip = max(1, int(fps // frame_skip_factor))

    all_stats = []
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_skip == 0:
            curr_kp, curr_desc, _, _ = extract_features(frame, xfeat, device)
            idx0, idx1 = match_descriptors(xfeat, ref_desc, curr_desc, match_threshold)
            n = len(idx0)
            ts = frame_idx / fps
            all_stats.append({"frame": frame_idx, "time": round(ts, 2), "matches": n})

            if progress_cb and total > 0:
                progress_cb(int(frame_idx / total * 100))

        frame_idx += 1

    cap.release()

    if not all_stats:
        return {"count": 0, "appearances": [], "stats": [], "fps": fps,
                "settings": {"high_thresh": 0, "low_thresh": 0, "adaptive": True}}

    # ── Rolling average smoothing ──────────────────────────────────────────
    raw_scores = [s["matches"] for s in all_stats]
    half_w = smoothing_window // 2
    smoothed = []
    for i in range(len(raw_scores)):
        lo = max(0, i - half_w)
        hi = min(len(raw_scores), i + half_w + 1)
        smoothed.append(sum(raw_scores[lo:hi]) / (hi - lo))

    # ── Adaptive thresholds ────────────────────────────────────────────────
    mean_score = sum(smoothed) / len(smoothed)
    variance = sum((x - mean_score) ** 2 for x in smoothed) / len(smoothed)
    std_score = variance ** 0.5

    # Safety: if signal is almost flat (std < 5% of mean), no clear separation
    if std_score < 0.05 * mean_score or std_score < 1:
        # Flat signal — treat whole video as 1 appearance if scores > 0
        if mean_score > 0:
            appearances = [{
                "start_time": all_stats[0]["time"],
                "end_time": all_stats[-1]["time"],
                "peak_matches": max(raw_scores),
                "peak_time": all_stats[raw_scores.index(max(raw_scores))]["time"],
                "frames_visible": len(all_stats)
            }]
        else:
            appearances = []
        return {
            "count": len(appearances),
            "appearances": appearances,
            "stats": all_stats,
            "fps": fps,
            "settings": {
                "high_thresh": round(mean_score, 1),
                "low_thresh": round(mean_score, 1),
                "adaptive": True,
                "note": "Flat signal — no clear peaks detected"
            }
        }

    high_thresh = mean_score + high_ratio * std_score
    low_thresh  = mean_score + low_ratio  * std_score
    low_thresh  = max(low_thresh, 0)  # never go negative

    # Min frames for gap and duration (derived from time params + frame rate)
    sample_fps   = fps / frame_skip  # actual samples per second
    min_gap_frames      = max(1, int(min_gap_sec * sample_fps))
    min_duration_frames = max(1, int(min_duration_sec * sample_fps))

    # ── Hysteresis state machine on smoothed scores ────────────────────────
    raw_appearances = []   # before gap-merging
    visible = False
    current_event = None
    consecutive_low = 0

    for i, stat in enumerate(all_stats):
        m_smooth = smoothed[i]
        m_raw    = raw_scores[i]

        if not visible:
            if m_smooth >= high_thresh:
                visible = True
                current_event = {
                    "start_time": stat["time"],
                    "peak_matches": m_raw,
                    "peak_time": stat["time"],
                    "frames_visible": 1,
                    "_end_idx": i,
                }
                consecutive_low = 0
        else:
            if m_smooth >= low_thresh:
                current_event["frames_visible"] += 1
                current_event["_end_idx"] = i
                consecutive_low = 0
                if m_raw > current_event["peak_matches"]:
                    current_event["peak_matches"] = m_raw
                    current_event["peak_time"]    = stat["time"]
            else:
                consecutive_low += 1
                if consecutive_low >= min_duration_frames:
                    # Object disappeared — record end at first low frame
                    end_idx = i - consecutive_low + 1
                    end_idx = max(0, min(end_idx, len(all_stats) - 1))
                    current_event["end_time"] = all_stats[end_idx]["time"]
                    raw_appearances.append(current_event)
                    current_event = None
                    visible = False
                    consecutive_low = 0

    # Close any open event at end of video
    if visible and current_event:
        current_event["end_time"] = all_stats[-1]["time"]
        raw_appearances.append(current_event)

    # ── Merge appearances that are too close together (gap < min_gap_sec) ─
    merged = []
    for app in raw_appearances:
        # Skip spuriously short appearances
        duration = app["end_time"] - app["start_time"]
        if duration < min_duration_sec and app["frames_visible"] < min_duration_frames:
            continue
        if merged:
            gap = app["start_time"] - merged[-1]["end_time"]
            if gap < min_gap_sec:
                # Merge with previous
                prev = merged[-1]
                prev["end_time"] = app["end_time"]
                prev["frames_visible"] += app["frames_visible"]
                if app["peak_matches"] > prev["peak_matches"]:
                    prev["peak_matches"] = app["peak_matches"]
                    prev["peak_time"]    = app["peak_time"]
                continue
        merged.append(app)

    # Clean up internal tracking keys
    for a in merged:
        a.pop("_end_idx", None)

    return {
        "count": len(merged),
        "appearances": merged,
        "stats": all_stats,
        "fps": fps,
        "settings": {
            "high_thresh": round(high_thresh, 1),
            "low_thresh":  round(low_thresh, 1),
            "mean_score":  round(mean_score, 1),
            "std_score":   round(std_score, 1),
            "adaptive":    True,
        }
    }


# ─────────────────────────────────────────────
# FEATURE 3 — Replace Object in Video (AR)
# Uses XFeat + homography + perspective warp
# ─────────────────────────────────────────────

def replace_object_in_video(query_path: str, video_path: str,
                             replacement_path: str, output_path: str,
                             frame_skip_factor: int = 5,
                             match_threshold: float = 0.80,
                             min_inliers: int = 12,
                             progress_cb=None) -> dict:
    """
    Detect the query object per frame, compute homography,
    and warp the replacement image onto the detected region.
    Outputs a new video file.
    """
    xfeat, device = get_model()

    query_img = cv2.imread(query_path)
    repl_img = cv2.imread(replacement_path)
    if query_img is None:
        return {"error": "Cannot read query image."}
    if repl_img is None:
        return {"error": "Cannot read replacement image."}

    ref_kp, ref_desc, _, ref_proc = extract_features(query_img, xfeat, device)
    ref_h, ref_w = ref_proc.shape[:2]

    # Resize replacement to match reference image dimensions
    repl_resized = cv2.resize(repl_img, (ref_w, ref_h))

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {"error": "Cannot open video."}

    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    vid_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    vid_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_skip = max(1, int(fps // frame_skip_factor))

    # Write to a temporary file first, then re-encode with FFmpeg for browser compatibility
    temp_output = output_path + ".tmp.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(temp_output, fourcc, fps, (vid_w, vid_h))

    frames_replaced = 0
    frame_idx = 0
    last_H = None  # reuse last valid homography for skipped frames

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_skip == 0:
            curr_kp, curr_desc, curr_scale, curr_proc = extract_features(frame, xfeat, device)
            idx0, idx1 = match_descriptors(xfeat, ref_desc, curr_desc, match_threshold)

            H = None
            if len(idx0) >= min_inliers:
                src_pts = ref_kp[idx0].cpu().numpy()
                dst_pts = curr_kp[idx1].cpu().numpy()

                # Scale keypoints back to original video frame size
                scale_x = vid_w / curr_proc.shape[1]
                scale_y = vid_h / curr_proc.shape[0]
                dst_pts_scaled = dst_pts * np.array([scale_x, scale_y])

                # Reference points in reference image coordinate space
                scale_ref_x = vid_w / ref_proc.shape[1] if ref_proc.shape[1] > 0 else 1
                scale_ref_y = vid_h / ref_proc.shape[0] if ref_proc.shape[0] > 0 else 1
                src_pts_scaled = src_pts * np.array([scale_ref_x, scale_ref_y])

                H_candidate, mask = cv2.findHomography(
                    src_pts_scaled.reshape(-1, 1, 2),
                    dst_pts_scaled.reshape(-1, 1, 2),
                    cv2.RANSAC, 5.0
                )
                if H_candidate is not None and mask is not None and mask.sum() >= min_inliers:
                    H = H_candidate
                    last_H = H

        # Use last valid H if current frame is skipped
        elif last_H is not None:
            H = last_H

        if H is not None:
            # Warp replacement image into frame
            repl_full = cv2.resize(repl_img, (vid_w, vid_h))
            warped = cv2.warpPerspective(repl_full, H, (vid_w, vid_h))

            # Build mask from the corner mapping of the query image
            corners = np.float32([[0, 0], [vid_w, 0], [vid_w, vid_h], [0, vid_h]]).reshape(-1, 1, 2)
            transformed = cv2.perspectiveTransform(corners, H)

            mask_img = np.zeros((vid_h, vid_w), dtype=np.uint8)
            cv2.fillPoly(mask_img, [np.int32(transformed)], 255)
            mask_3ch = cv2.merge([mask_img, mask_img, mask_img])

            # Blend
            frame_out = np.where(mask_3ch > 0, warped, frame)
            frames_replaced += 1
        else:
            frame_out = frame

        writer.write(frame_out)
        frame_idx += 1

        if progress_cb and total > 0:
            progress_cb(int(frame_idx / total * 100))

    cap.release()
    writer.release()

    # ── Re-encode with FFmpeg to H.264 for browser-compatible playback ──
    # Try imageio-ffmpeg bundled binary first, then system path
    ffmpeg_bin = None
    try:
        import imageio_ffmpeg
        ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
        print(f"[FFmpeg] Found via imageio-ffmpeg: {ffmpeg_bin}")
    except (ImportError, Exception):
        ffmpeg_bin = shutil.which("ffmpeg")
        if ffmpeg_bin:
            print(f"[FFmpeg] Found on system PATH: {ffmpeg_bin}")

    if ffmpeg_bin:
        try:
            cmd = [
                ffmpeg_bin, "-y", "-i", temp_output,
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                output_path,
            ]
            print(f"[FFmpeg] Re-encoding for browser: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode == 0:
                os.remove(temp_output)
                print("[FFmpeg] Re-encoding complete — H.264 browser-ready video created.")
            else:
                print(f"[FFmpeg] Failed (rc={result.returncode}): {result.stderr[:500]}")
                # Fall back to the raw OpenCV output
                shutil.move(temp_output, output_path)
        except Exception as e:
            print(f"[FFmpeg] Error during re-encoding: {e}")
            shutil.move(temp_output, output_path)
    else:
        print("[WARN] FFmpeg not found — video may not play in browser.")
        shutil.move(temp_output, output_path)

    return {
        "output_path": output_path,
        "frames_replaced": frames_replaced,
        "total_frames": frame_idx,
        "fps": fps,
    }
