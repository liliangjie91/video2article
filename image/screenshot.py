"""Step 2: 视频关键帧提取 + 图文合成"""

import json
import os
import subprocess
import logging
import re

logger = logging.getLogger(__name__)


def _parse_ts_to_seconds(ts_str: str) -> float:
    """Parse 'HH:MM:SS' or 'HH:MM:SS-HH:MM:SS' to midpoint seconds."""
    m = re.match(r"(\d{2}):(\d{2}):(\d{2})", ts_str)
    if not m:
        return 0.0
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))


def _time_range_midpoint(time_range: str) -> float:
    """Given '00:00-05:30' or '00:00:00-00:05:30', return midpoint in seconds."""
    parts = time_range.split("-")
    start = _parse_ts_to_seconds(parts[0].strip())
    end = _parse_ts_to_seconds(parts[1].strip()) if len(parts) > 1 else start + 60
    return (start + end) / 2


def extract_screenshots(
    video_path: str,
    structure_path: str,
    output_dir: str,
    frames_per_segment: int = 1,
) -> list[str]:
    """Extract key frames from video at each segment's midpoint.

    Returns list of screenshot file paths.
    """
    os.makedirs(output_dir, exist_ok=True)

    with open(structure_path, "r", encoding="utf-8") as f:
        structure = json.load(f)

    screenshots = []
    for seg in structure.get("segments", []):
        time_range = seg.get("time_range", "00:00-01:00")
        midpoint = _time_range_midpoint(time_range)
        ts_label = time_range.replace(":", "").replace("-", "_")

        for i in range(frames_per_segment):
            offset = midpoint + (i - frames_per_segment / 2 + 0.5) * 5  # spread 5s apart
            ts_display = f"{int(offset // 3600):02d}:{int(offset % 3600 // 60):02d}:{int(offset % 60):02d}"
            filename = f"seg_{seg['id']:02d}_{ts_display.replace(':', '')}.jpg"
            filepath = os.path.join(output_dir, filename)

            cmd = [
                "ffmpeg", "-y",
                "-ss", str(offset),
                "-i", video_path,
                "-frames:v", "1",
                "-q:v", "2",
                filepath,
            ]
            subprocess.run(cmd, capture_output=True, check=False)
            if os.path.exists(filepath):
                screenshots.append(filepath)
                logger.info("Screenshot: %s (ts=%.1fs)", filename, offset)
            else:
                logger.warning("Failed to capture: %s", filename)

    return screenshots


def synthesize_illustrated(
    article_path: str,
    screenshots: list[str],
    structure_path: str,
    output_dir: str,
) -> str:
    """Insert screenshot references into the article, producing 05_illustrated.md.

    Strategy: insert screenshots after the nearest ## heading that matches each segment.
    Falls back to appending all screenshots at the end.
    """
    os.makedirs(output_dir, exist_ok=True)

    with open(article_path, "r", encoding="utf-8") as f:
        article = f.read()

    with open(structure_path, "r", encoding="utf-8") as f:
        structure = json.load(f)

    segments = structure.get("segments", [])

    # Build a mapping: segment_topic → screenshot_path
    # Screenshots are named seg_XX_HHMMSS.jpg
    ss_map = {}
    for ss in screenshots:
        basename = os.path.basename(ss)
        m = re.match(r"seg_(\d+)_", basename)
        if m:
            seg_id = int(m.group(1))
            rel_path = os.path.join("screenshots", basename)
            ss_map.setdefault(seg_id, []).append(rel_path)

    # Simple insertion: append a ## 配图 section with all screenshots referenced by segment
    # This is reliable and doesn't depend on LLM-generated heading matching
    img_section_parts = ["\n\n## 配图\n"]
    for seg in segments:
        seg_id = seg["id"]
        if seg_id in ss_map:
            topic = seg.get("topic", f"段落{seg_id}")
            img_section_parts.append(f"\n**{topic}** ({seg.get('time_range', '')})\n")
            for rel in ss_map[seg_id]:
                img_section_parts.append(f"![{topic}]({rel})\n")

    illustrated = article.rstrip() + "\n" + "".join(img_section_parts)

    output_path = os.path.join(output_dir, "05_illustrated.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(illustrated)

    logger.info("Illustrated article: %s", output_path)
    return output_path
