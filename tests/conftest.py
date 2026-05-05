import pytest


# ── Sample subtitle content ──────────────────────────────────────


@pytest.fixture
def sample_srt():
    return (
        "1\n"
        "00:00:01,000 --> 00:00:04,000\n"
        "Hello world, this is a test.\n"
        "\n"
        "2\n"
        "00:00:05,000 --> 00:00:08,500\n"
        "Second subtitle line here.\n"
        "\n"
        "3\n"
        "00:00:09,000 --> 00:00:12,000\n"
        "Third and final line.\n"
    )


@pytest.fixture
def sample_srt_dot():
    """SRT with dots instead of commas in timestamps (some generators)."""
    return (
        "1\n"
        "00:00:01.000 --> 00:00:04.000\n"
        "Dot timestamp line.\n"
    )


@pytest.fixture
def sample_vtt():
    return (
        "WEBVTT\n"
        "\n"
        "00:00:01.000 --> 00:00:04.000\n"
        "Hello from VTT.\n"
        "\n"
        "00:00:05.000 --> 00:00:08.500\n"
        "Second VTT line.\n"
    )


@pytest.fixture
def sample_vtt_with_tags():
    return (
        "WEBVTT\n"
        "\n"
        "00:00:01.000 --> 00:00:04.000\n"
        "<c.hand>Hello</c> <v Narrator>from tagged VTT</v>.\n"
    )


@pytest.fixture
def sample_vtt_with_cue_label():
    return (
        "WEBVTT\n"
        "\n"
        "This is a cue label\n"
        "00:00:01.000 --> 00:00:04.000\n"
        "Text after a cue label.\n"
    )


@pytest.fixture
def sample_simple():
    return (
        "[00:00:01] Hello world, simple format.\n"
        "[00:00:05] Second line here.\n"
        "[00:00:09] Third and final line.\n"
    )


@pytest.fixture
def sample_simple_single():
    return "[00:01:30] Only one line.\n"
