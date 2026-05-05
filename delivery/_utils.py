"""Internal utilities for delivery channel implementations."""


def split_text(text: str, max_len: int) -> list[str]:
    """Split *text* into chunks no longer than *max_len* at paragraph boundaries."""
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for para in text.split("\n\n"):
        para_len = len(para) + 2  # +2 for the "\n\n" separator
        if current_len + para_len > max_len:
            if current:
                chunks.append("\n\n".join(current))
            current = [para]
            current_len = len(para)
        else:
            current.append(para)
            current_len += para_len

    if current:
        chunks.append("\n\n".join(current))

    return chunks
