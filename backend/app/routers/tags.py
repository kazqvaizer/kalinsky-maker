from fastapi import APIRouter, HTTPException

from app import state
from app.models.tag import Tag, TagCreate, TagUpdate

router = APIRouter(prefix="/api/v1/tags", tags=["tags"])


@router.get("", response_model=list[Tag])
async def list_tags():
    return await state.list_tags()


@router.post("", response_model=Tag, status_code=201)
async def create_tag(body: TagCreate):
    tag = await state.create_tag(body.name, body.color)
    if not tag:
        raise HTTPException(status_code=409, detail=f"Tag '{body.name}' already exists")
    return tag


@router.put("/{tag_id}", response_model=Tag)
async def rename_tag(tag_id: int, body: TagUpdate):
    tag = await state.rename_tag(tag_id, body.name)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


@router.delete("/{tag_id}", status_code=204)
async def delete_tag(tag_id: int):
    deleted = await state.delete_tag(tag_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Tag not found")
