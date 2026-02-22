import asyncio
from pathlib import Path

from app.config import FFMPEG_BIN


async def concat_segments(segment_paths: list[Path], output_path: Path) -> None:
    list_file = output_path.parent / "concat_list.txt"
    list_file.write_text("\n".join(f"file '{p.resolve()}'" for p in segment_paths))

    cmd = [
        FFMPEG_BIN, "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(output_path),
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg concat failed: {stderr.decode()}")
