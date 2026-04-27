"""Parse subtitle files into a uniform internal format.

Supported formats: SRT, VTT, Simple ([HH:MM:SS] text per line)
Internal format: list of (start_ms: int, end_ms: int, text: str)
"""

import re


def _parse_hhmmss(ts: str) -> int:
    """Parse HH:MM:SS or HH:MM:SS.mmm to milliseconds."""
    m = re.match(r"(\d{2}):(\d{2}):(\d{2})(?:[.,](\d{3}))?", ts)
    if not m:
        return 0
    ms = int(m.group(4)) if m.group(4) else 0
    return int(m.group(1)) * 3600000 + int(m.group(2)) * 60000 + int(m.group(3)) * 1000 + ms


def parse_simple(filepath: str) -> list[tuple[int, int, str]]:
    """Parse simple [HH:MM:SS] text format (one timestamp per line)."""
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    entries = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        m = re.match(r"\[(\d{2}:\d{2}:\d{2})\]\s*(.*)", line)
        if m:
            start_ms = _parse_hhmmss(m.group(1))
            text = m.group(2).strip()
            if text:
                entries.append((start_ms, text))

    # Assign end times: use next entry's start, or +3s for the last
    result = []
    for i, (start_ms, text) in enumerate(entries):
        if i + 1 < len(entries):
            end_ms = entries[i + 1][0]
        else:
            end_ms = start_ms + 3000
        result.append((start_ms, end_ms, text))

    return result


def parse_srt(filepath: str) -> list[tuple[int, int, str]]:
    """Parse an SRT subtitle file."""
    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()

    blocks = re.split(r"\n\s*\n", raw.strip())
    result = []

    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue
        # Line 0 = index, Line 1 = timestamp, Line 2+ = text
        ts_match = re.match(
            r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})",
            lines[1],
        )
        if not ts_match:
            continue
        start_ms = (
            int(ts_match.group(1)) * 3600000
            + int(ts_match.group(2)) * 60000
            + int(ts_match.group(3)) * 1000
            + int(ts_match.group(4))
        )
        end_ms = (
            int(ts_match.group(5)) * 3600000
            + int(ts_match.group(6)) * 60000
            + int(ts_match.group(7)) * 1000
            + int(ts_match.group(8))
        )
        text = " ".join(lines[2:]).strip()
        if text:
            result.append((start_ms, end_ms, text))

    return result


def parse_vtt(filepath: str) -> list[tuple[int, int, str]]:
    """Parse a WebVTT subtitle file."""
    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()

    # Strip WEBVTT header
    raw = re.sub(r"^WEBVTT.*\n", "", raw)
    blocks = re.split(r"\n\s*\n", raw.strip())
    result = []

    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 2:
            continue
        ts_match = re.match(
            r"(\d{2}):(\d{2}):(\d{2})[.,](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[.,](\d{3})",
            lines[0],
        )
        if not ts_match:
            # Could have optional cue label before timestamp
            if len(lines) >= 2:
                ts_match = re.match(
                    r"(\d{2}):(\d{2}):(\d{2})[.,](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[.,](\d{3})",
                    lines[1],
                )
                text_lines = lines[2:]
            else:
                continue
        else:
            text_lines = lines[1:]

        if not ts_match:
            continue

        start_ms = (
            int(ts_match.group(1)) * 3600000
            + int(ts_match.group(2)) * 60000
            + int(ts_match.group(3)) * 1000
            + int(ts_match.group(4))
        )
        end_ms = (
            int(ts_match.group(5)) * 3600000
            + int(ts_match.group(6)) * 60000
            + int(ts_match.group(7)) * 1000
            + int(ts_match.group(8))
        )
        # Remove VTT tags like <c> <v> etc.
        text = " ".join(text_lines).strip()
        text = re.sub(r"<[^>]+>", "", text)
        if text:
            result.append((start_ms, end_ms, text))

    return result


def parse(filepath: str) -> list[tuple[int, int, str]]:
    """Auto-detect format and parse a subtitle file."""
    # Read first line to detect simple format
    with open(filepath, "r", encoding="utf-8") as f:
        first_line = f.readline().strip()
    if re.match(r"\[\d{2}:\d{2}:\d{2}\]", first_line):
        return parse_simple(filepath)

    ext = filepath.rsplit(".", 1)[-1].lower()
    if ext == "srt":
        return parse_srt(filepath)
    elif ext == "vtt":
        return parse_vtt(filepath)
    else:
        raise ValueError(f"Unsupported subtitle format: .{ext}")


def format_timestamp(ms: int) -> str:
    """Convert milliseconds to HH:MM:SS string."""
    s, ms = divmod(ms, 1000)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def to_text(subtitles: list[tuple[int, int, str]]) -> str:
    """Convert parsed subtitles to a plain text blob with timestamps."""
    lines = []
    for start_ms, end_ms, text in subtitles:
        ts = format_timestamp(start_ms)
        lines.append(f"[{ts}] {text}")
    return "\n".join(lines)
