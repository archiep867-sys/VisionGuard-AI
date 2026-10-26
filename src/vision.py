from __future__ import annotations
import cv2
import numpy as np
from pathlib import Path


def _zone_polygon(width: int, height: int) -> np.ndarray:
    """Default restricted zone: lower-right region. Replace/configure for a real scene."""
    return np.array([
        [int(width * 0.55), int(height * 0.35)],
        [int(width * 0.95), int(height * 0.35)],
        [int(width * 0.95), int(height * 0.95)],
        [int(width * 0.55), int(height * 0.95)],
    ], dtype=np.int32)


def analyze_video(video_path: str, sample_every: int = 5, min_motion_pixels: int = 700, confirm_frames: int = 2) -> dict:
    """Detect sustained foreground motion inside a fixed zone and run an evidence-driven follow-up.

    Agentic loop: initial zone-motion detection changes the plan to inspect subsequent samples.
    Events are motion alerts, not person identity or definitive safety-violation detections.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError("Could not open the video. Try MP4/H.264 or AVI.")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    bg = cv2.createBackgroundSubtractorMOG2(history=250, varThreshold=32, detectShadows=False)
    events, trace, annotated = [], [], []
    frames_inspected = motion_events = follow_up_checks = 0
    consecutive_zone_motion = 0
    event_open = False
    frame_index = 0
    zone_mask = None
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            current_index = frame_index
            frame_index += 1
            if current_index % max(1, sample_every) != 0:
                continue
            frames_inspected += 1
            h, w = frame.shape[:2]
            polygon = _zone_polygon(w, h)
            if zone_mask is None or zone_mask.shape[:2] != (h, w):
                zone_mask = np.zeros((h, w), dtype=np.uint8)
                cv2.fillPoly(zone_mask, [polygon], 255)

            # Substantive OpenCV processing: background subtraction, morphology, ROI masking,
            # contour extraction, and annotated evidence frames.
            fg = bg.apply(frame)
            fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, kernel, iterations=1)
            fg = cv2.dilate(fg, kernel, iterations=2)
            zone_motion = cv2.bitwise_and(fg, zone_mask)
            motion_pixels = int(cv2.countNonZero(zone_motion))
            contours, _ = cv2.findContours(zone_motion, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            large_contours = [c for c in contours if cv2.contourArea(c) >= 180]
            motion_present = motion_pixels >= int(min_motion_pixels) and bool(large_contours)

            if motion_present:
                motion_events += 1
                consecutive_zone_motion += 1
                if not event_open:
                    trace.append({"step": "PERCEIVE", "message": f"Zone motion observed at {current_index / fps:.1f}s ({motion_pixels} foreground pixels)."})
                    trace.append({"step": "PLAN", "message": "Motion is not yet confirmed; agent schedules follow-up frame checks instead of immediately raising a confirmed alert."})
                    event_open = True
                else:
                    follow_up_checks += 1
                    trace.append({"step": "VERIFY", "message": f"Follow-up sample at {current_index / fps:.1f}s: {motion_pixels} foreground pixels in the zone."})
                if consecutive_zone_motion >= max(1, confirm_frames) and not any(e.get("status") == "CONFIRMED_MOTION" and e.get("end_seconds") is None for e in events):
                    events.append({
                        "start_seconds": round(current_index / fps, 2),
                        "end_seconds": None,
                        "status": "CONFIRMED_MOTION",
                        "peak_motion_pixels": motion_pixels,
                        "human_review_required": True,
                        "interpretation": "Sustained motion in configured zone; not proof of a safety violation.",
                    })
                    trace.append({"step": "ACT", "message": "Sustained motion confirmed. Agent records an incident candidate and requests human review."})
            else:
                if event_open and consecutive_zone_motion > 0:
                    trace.append({"step": "VERIFY", "message": f"Zone motion no longer present at {current_index / fps:.1f}s; agent closes the observation window."})
                consecutive_zone_motion = 0
                event_open = False
                for e in reversed(events):
                    if e.get("end_seconds") is None:
                        e["end_seconds"] = round(current_index / fps, 2)
                        break

            view = frame.copy()
            cv2.polylines(view, [polygon], True, (0, 165, 255), 3)
            label = f"ZONE MOTION: {motion_pixels}px" if motion_present else f"Zone motion: {motion_pixels}px"
            cv2.putText(view, label, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 255) if motion_present else (0, 255, 0), 2, cv2.LINE_AA)
            cv2.putText(view, f"Frame {current_index} | OpenCV {cv2.__version__}", (12, h - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
            if len(annotated) < 12:
                annotated.append(view)
    finally:
        cap.release()

    if not frames_inspected:
        raise ValueError("No readable frames found in the video.")
    confirmed = sum(1 for e in events if e["status"] == "CONFIRMED_MOTION")
    if not trace:
        trace.append({"step": "PERCEIVE", "message": "No zone motion met the configured threshold in sampled frames."})
        trace.append({"step": "DECIDE", "message": "No follow-up inspection was triggered because the initial visual evidence did not cross the threshold."})
    return {
        "events": events,
        "annotated_frames": annotated,
        "agent_trace": trace[-30:],
        "summary": {
            "frames_inspected": frames_inspected,
            "motion_events": motion_events,
            "confirmed_events": confirmed,
            "follow_up_checks": follow_up_checks,
            "video_frames": frame_count,
        },
    }


def make_demo_video(path: str, width: int = 640, height: int = 360, frames: int = 150, fps: int = 25) -> str:
    """Create a synthetic clip with a moving high-contrast object entering the configured zone."""
    out = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"MJPG"), fps, (width, height))
    if not out.isOpened():
        raise RuntimeError("Could not create demo video; video codec unavailable.")
    try:
        for i in range(frames):
            frame = np.full((height, width, 3), 238, dtype=np.uint8)
            # Static scene markings and a zone similar to the analysis ROI.
            cv2.rectangle(frame, (20, 20), (width - 20, height - 20), (210, 210, 210), 2)
            x = 60 + int(i * 3.4)
            y = 220
            cv2.rectangle(frame, (x, y - 45), (x + 28, y + 15), (30, 30, 30), -1)
            cv2.circle(frame, (x + 14, y - 55), 12, (30, 30, 30), -1)
            cv2.putText(frame, "SYNTHETIC DEMO - NOT REAL FOOTAGE", (20, height - 32), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (80, 80, 80), 1, cv2.LINE_AA)
            out.write(frame)
    finally:
        out.release()
    return path
