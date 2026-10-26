from pathlib import Path
import cv2
from src.vision import make_demo_video, analyze_video


def test_demo_video_and_analysis(tmp_path: Path):
    video = tmp_path / "demo.avi"
    make_demo_video(str(video), frames=50)
    assert video.exists() and video.stat().st_size > 0
    result = analyze_video(str(video), sample_every=2, min_motion_pixels=100, confirm_frames=1)
    assert result["summary"]["frames_inspected"] > 0
    assert "events" in result
    assert "agent_trace" in result
    assert cv2.__version__.startswith("5.")
