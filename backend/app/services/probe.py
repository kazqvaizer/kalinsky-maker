import asyncio
import json

from app.config import FFPROBE_BIN


async def ffprobe(path: str) -> dict:
    proc = await asyncio.create_subprocess_exec(
        FFPROBE_BIN,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    return json.loads(stdout)


async def probe_video(path: str) -> dict:
    """Return dict with duration, resolution, codec for a video file."""
    data = await ffprobe(path)
    video_stream = next((s for s in data.get("streams", []) if s["codec_type"] == "video"), None)
    duration = float(data["format"]["duration"])
    if video_stream:
        w = video_stream["width"]
        h = video_stream["height"]
        resolution = f"{w}x{h}"
        codec = video_stream["codec_name"]
    else:
        resolution = "unknown"
        codec = "unknown"
    return {"duration": duration, "resolution": resolution, "codec": codec}
