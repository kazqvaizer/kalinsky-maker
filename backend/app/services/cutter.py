import asyncio
from pathlib import Path

from app.config import AUDIO_BITRATE, AUDIO_CODEC, AUDIO_FADE_MS, FFMPEG_BIN, SOURCES_DIR


async def cut_segment(
    filename: str,
    start: float,
    end: float,
    output_path: Path,
    preview: bool,
    pos: int = 0,
) -> None:
    duration = end - start
    fade_sec = AUDIO_FADE_MS / 1000.0
    fade_out_start = max(0, duration - fade_sec)

    input_path = str(SOURCES_DIR / filename)

    if preview:
        safe_name = filename.replace("'", "\\'").replace(":", "\\:")
        label = f"[{pos}] {safe_name}"
        vf = (
            "setpts=PTS-STARTPTS,scale=-2:720,"
            f"drawtext=text='{label}':x=10:y=10:fontsize=24:fontcolor=white:borderw=2:bordercolor=black,"
            f"drawtext=text='%{{pts\\:hms}}':x=10:y=38:fontsize=24:fontcolor=white:borderw=2:bordercolor=black"
        )
        cmd = [
            FFMPEG_BIN, "-nostdin", "-y",
            "-ss", str(start),
            "-t", str(duration),
            "-i", input_path,
            "-vf", vf,
            "-af", f"asetpts=PTS-STARTPTS,"
                   f"afade=t=in:st=0:d={fade_sec},afade=t=out:st={fade_out_start}:d={fade_sec}",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
            "-c:a", AUDIO_CODEC, "-b:a", AUDIO_BITRATE,
            "-shortest", "-fflags", "+igndts",
            str(output_path),
        ]
    else:
        # Stream copy video — no re-encode. Use keyframe-accurate seek.
        cmd = [
            FFMPEG_BIN, "-nostdin", "-y",
            "-ss", str(start),
            "-to", str(end),
            "-i", input_path,
            "-c:v", "copy",
            "-af", f"afade=t=in:st=0:d={fade_sec},afade=t=out:st={fade_out_start}:d={fade_sec}",
            "-c:a", AUDIO_CODEC, "-b:a", AUDIO_BITRATE,
            str(output_path),
        ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg cut failed: {stderr.decode()}")
