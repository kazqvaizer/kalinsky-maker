import asyncio
import math

from fastapi import APIRouter, HTTPException

from pydantic import BaseModel

from app import state
from app.config import FFMPEG_BIN, PREVIEWS_DIR, SOURCES_DIR
from app.models.source import Source
from app.services.probe import probe_video

router = APIRouter(prefix="/api/v1/sources", tags=["sources"])

EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}


async def generate_thumbnail(video_path: str, thumb_path: str) -> None:
    cmd = [
        FFMPEG_BIN, "-nostdin", "-y",
        "-ss", "0.5",
        "-i", video_path,
        "-vframes", "1",
        "-vf", "scale=320:-1",
        str(thumb_path),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    await proc.communicate()


@router.post("/reindex")
async def reindex():
    PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(
        f for f in SOURCES_DIR.iterdir() if f.is_file() and f.suffix.lower() in EXTENSIONS
    )
    sources: list[Source] = []
    for i, f in enumerate(files, 1):
        info = await probe_video(str(f))
        sources.append(
            Source(
                index=i,
                filename=f.name,
                duration=math.floor((info["duration"] - 0.1) * 10) / 10,
                resolution=info["resolution"],
                codec=info["codec"],
                file_size=f.stat().st_size,
            )
        )
        thumb = PREVIEWS_DIR / (f.stem + ".jpg")
        if not thumb.exists():
            await generate_thumbnail(str(f), str(thumb))
    await state.set_sources(sources)
    return {"status": "ok", "count": len(sources)}


class SourceTagsBody(BaseModel):
    tag_ids: list[int]


@router.put("/{index}/tags")
async def set_source_tags(index: int, body: SourceTagsBody):
    sources = await state.get_sources()
    src = next((s for s in sources if s.index == index), None)
    if not src:
        raise HTTPException(status_code=404, detail=f"Source {index} not found")
    await state.set_source_tags(src.filename, body.tag_ids)
    return {"status": "ok"}


@router.get("", response_model=list[Source])
async def list_sources():
    sources = await state.get_sources()
    if not sources:
        raise HTTPException(status_code=409, detail="No index. Call POST /sources/reindex first.")
    return sources
