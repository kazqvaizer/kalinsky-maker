import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app import state
from app.models.assembly import Assembly, AssemblyCreate, AssemblyUpdate, ClipDetail
from app.models.source import Source
from app.services.assembly import run_assembly

router = APIRouter(prefix="/api/v1/assemblies", tags=["assemblies"])


def _resolve_source(ref: int | str, sources: list[Source]) -> Source:
    for s in sources:
        if isinstance(ref, int) and s.index == ref:
            return s
        if isinstance(ref, str) and s.filename == ref:
            return s
    raise HTTPException(status_code=422, detail=f"Source {ref!r} not found")


@router.post("", response_model=Assembly, status_code=202)
async def create_assembly(body: AssemblyCreate):
    sources = await state.get_sources()
    if not sources:
        raise HTTPException(status_code=409, detail="No index. Call POST /sources/reindex first.")
    if not body.clips:
        raise HTTPException(status_code=422, detail="Empty clips list")

    clips: list[ClipDetail] = []
    for i, c in enumerate(body.clips, 1):
        src = _resolve_source(c.source, sources)
        start = c.start or 0
        end = c.end if c.end is not None else src.duration
        end = min(end, src.duration)
        if start >= end:
            raise HTTPException(status_code=422, detail=f"start >= end for clip {i}")
        if start < 0:
            raise HTTPException(status_code=422, detail=f"start/end exceeds duration for clip {i}")
        clips.append(ClipDetail(pos=i, filename=src.filename, start=start, end=end, duration=end - start))

    asm_id = await state.next_assembly_id()
    asm = Assembly(
        id=asm_id,
        name=body.name,
        status="processing",
        preview=body.preview,
        clips=clips,
        created=datetime.now(timezone.utc).isoformat(),
    )
    await state.save_assembly(asm)
    task = asyncio.create_task(run_assembly(asm))
    state.assembly_tasks[asm_id] = task
    return asm


@router.get("", response_model=list[Assembly])
async def list_assemblies():
    return await state.list_assemblies()


@router.get("/{assembly_id}", response_model=Assembly)
async def get_assembly(assembly_id: str):
    asm = await state.get_assembly(assembly_id)
    if not asm:
        raise HTTPException(status_code=404, detail="Assembly not found")
    return asm


@router.patch("/{assembly_id}", response_model=Assembly)
async def update_assembly(assembly_id: str, body: AssemblyUpdate):
    updated = await state.update_assembly_note(assembly_id, body.note)
    if not updated:
        raise HTTPException(status_code=404, detail="Assembly not found")
    return await state.get_assembly(assembly_id)


@router.delete("/{assembly_id}", status_code=204)
async def delete_assembly(assembly_id: str):
    deleted = await state.delete_assembly(assembly_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Assembly not found")
    task = state.assembly_tasks.pop(assembly_id, None)
    if task and not task.done():
        task.cancel()
