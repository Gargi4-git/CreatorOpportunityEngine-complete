"""Media handling: validation, ffmpeg audio extraction and frame sampling, transcript chunking."""
import re
import subprocess
import tempfile
from pathlib import Path
from typing import List

IMAGE_EXT = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
AUDIO_EXT = {".mp3", ".wav", ".m4a"}
VIDEO_EXT = {".mp4", ".mov"}
MAGIC = {".png": b"\x89PNG", ".jpg": b"\xff\xd8", ".jpeg": b"\xff\xd8", ".webp": b"RIFF", ".wav": b"RIFF",
         ".mp3": (b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"), ".m4a": b"", ".mp4": b"", ".mov": b""}


class MediaError(ValueError):
    """Safe to show to the user."""


def check_magic(ext: str, head: bytes) -> bool:
    """Verify the file's leading bytes match its extension (don't trust the filename alone)."""
    if ext in (".mp4", ".m4a", ".mov"):
        return b"ftyp" in head[:32] or head[4:8] in (b"moov", b"mdat", b"wide", b"free")
    m = MAGIC.get(ext)
    return bool(m) and head.startswith(m)


def chunk_transcript(text: str, max_chars: int = 400) -> List[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    chunks, cur = [], ""
    for s in sentences:
        if cur and len(cur) + len(s) > max_chars:
            chunks.append(cur.strip()); cur = ""
        cur += " " + s
    if cur.strip():
        chunks.append(cur.strip())
    return [c for c in chunks if len(c) >= 8]


def _run(cmd: List[str], timeout: int = 300):
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=timeout)
    except FileNotFoundError:
        raise MediaError("ffmpeg is not installed on the server.")
    except subprocess.TimeoutExpired:
        raise MediaError("Processing this video took too long. Try a shorter clip.")
    except subprocess.CalledProcessError:
        raise MediaError("The media file could not be processed. It may be corrupt or unsupported.")


def extract_audio(video_path: str, out_wav: str) -> None:
    _run(["ffmpeg", "-y", "-i", video_path, "-vn", "-ac", "1", "-ar", "16000", out_wav])


def duration_seconds(path: str) -> float:
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                             check=True, capture_output=True, timeout=30, text=True).stdout.strip()
        return float(out)
    except Exception:
        raise MediaError("Could not read the video duration. The file may be corrupt.")


def extract_frames(video_path: str, n: int = 6) -> List[bytes]:
    """n evenly spaced JPEG frames (representative sampling)."""
    dur = duration_seconds(video_path)
    frames = []
    with tempfile.TemporaryDirectory() as d:
        for i in range(n):
            t = dur * (i + 0.5) / n
            out = str(Path(d) / f"f{i}.jpg")
            _run(["ffmpeg", "-y", "-ss", f"{t:.2f}", "-i", video_path, "-frames:v", "1", "-vf", "scale=768:-2", out], timeout=60)
            if Path(out).exists():
                frames.append(Path(out).read_bytes())
    if not frames:
        raise MediaError("No frames could be extracted from this video.")
    return frames
