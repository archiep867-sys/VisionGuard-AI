from __future__ import annotations
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import cv2
import streamlit as st
import pandas as pd
from src.vision import analyze_video, make_demo_video
from src.storage import upload_evidence

st.set_page_config(page_title="VisionGuard AI", page_icon="🛡️", layout="wide")
st.title("🛡️ VisionGuard AI")
st.caption("Agentic visual safety monitoring • OpenCV 5 • AWS-ready evidence archive")

with st.sidebar:
    st.header("Analysis settings")
    sample_every = st.slider("Analyze every Nth frame", 1, 15, 5)
    min_motion = st.slider("Minimum motion pixels in zone", 100, 5000, 700, 100)
    confirm_frames = st.slider("Confirm across this many sampled frames", 1, 5, 2)
    st.markdown("---")
    st.caption("This prototype detects sustained motion inside a user-defined restricted zone. It does not identify people or prove that a real safety violation occurred.")

uploaded = st.file_uploader("Upload a video (MP4, MOV, AVI)", type=["mp4", "mov", "avi", "m4v"])
use_demo = st.button("Create and analyze a demo video", type="secondary")

if use_demo:
    with st.spinner("Creating a small synthetic demo clip…"):
        demo_path = Path(tempfile.gettempdir()) / "visionguard_demo.avi"
        make_demo_video(str(demo_path))
        result = analyze_video(str(demo_path), sample_every, min_motion, confirm_frames)
    st.session_state["visionguard_result"] = result
    st.session_state["visionguard_name"] = "synthetic_demo.avi"

if uploaded is not None and st.button("Analyze uploaded video", type="primary"):
    suffix = Path(uploaded.name).suffix or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.getvalue())
        video_path = tmp.name
    try:
        with st.spinner("Analyzing frames and running the agent's follow-up checks…"):
            result = analyze_video(video_path, sample_every, min_motion, confirm_frames)
        st.session_state["visionguard_result"] = result
        st.session_state["visionguard_name"] = uploaded.name
    finally:
        try:
            os.unlink(video_path)
        except OSError:
            pass

result = st.session_state.get("visionguard_result")
if result:
    st.subheader("Analysis result")
    metrics = st.columns(4)
    metrics[0].metric("Frames inspected", result["summary"]["frames_inspected"])
    metrics[1].metric("Zone motion events", result["summary"]["motion_events"])
    metrics[2].metric("Confirmed events", result["summary"]["confirmed_events"])
    metrics[3].metric("Agent follow-up checks", result["summary"]["follow_up_checks"])

    st.markdown("### Agent trace")
    for item in result["agent_trace"]:
        st.write(f"**{item['step']}** — {item['message']}")

    st.markdown("### Annotated evidence")
    if result["annotated_frames"]:
        cols = st.columns(min(3, len(result["annotated_frames"])))
        for i, frame in enumerate(result["annotated_frames"][:3]):
            with cols[i % len(cols)]:
                st.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), caption=f"Evidence frame {i+1}", use_container_width=True)
    else:
        st.info("No sample frames were available to display.")

    st.markdown("### Event timeline")
    if result["events"]:
        st.dataframe(pd.DataFrame(result["events"]), use_container_width=True, hide_index=True)
    else:
        st.success("No sustained motion was confirmed inside the configured zone in this clip.")

    report = {
        "project": "VisionGuard AI",
        "source_video": st.session_state.get("visionguard_name", "uploaded_video"),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "opencv_version": cv2.__version__,
        "summary": result["summary"],
        "events": result["events"],
        "agent_trace": result["agent_trace"],
        "limitations": "Motion-based prototype; does not identify people or establish real-world safety violations. Human review required.",
    }
    import json
    report_bytes = json.dumps(report, indent=2).encode("utf-8")
    st.download_button("Download incident report (JSON)", report_bytes, file_name="visionguard_report.json", mime="application/json")
    st.download_button("Download events (CSV)", pd.DataFrame(result["events"]).to_csv(index=False).encode("utf-8"), file_name="visionguard_events.csv", mime="text/csv")

    if st.button("Archive report to AWS S3"):
        with st.spinner("Uploading report to configured S3 bucket…"):
            ok, message = upload_evidence(report_bytes, "reports/visionguard_report.json")
        if ok:
            st.success(message)
        else:
            st.error(message)
            st.info("Configure AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION and S3_BUCKET as environment variables. Use an IAM role in AWS deployments where possible.")

st.markdown("---")
st.caption("Research/demo prototype only. Use consented test footage, do not use it as the sole basis for safety enforcement, and have a human verify alerts.")
