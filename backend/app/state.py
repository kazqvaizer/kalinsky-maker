import asyncio

from app.db import get_db
from app.models.assembly import Assembly, ClipDetail
from app.models.source import Source
from app.models.tag import Tag

# Task refs are not serializable — keep in memory
assembly_tasks: dict[str, asyncio.Task] = {}


async def get_sources() -> list[Source]:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT idx, filename, duration, resolution, codec, file_size FROM sources ORDER BY idx"
        )
        rows = await cursor.fetchall()
        filenames = [r["filename"] for r in rows]
        tags_map = await _get_tags_for_filenames(db, filenames)
        return [
            Source(index=r["idx"], filename=r["filename"], duration=r["duration"],
                   resolution=r["resolution"], codec=r["codec"], file_size=r["file_size"],
                   tags=tags_map.get(r["filename"], []))
            for r in rows
        ]
    finally:
        await db.close()


async def _get_tags_for_filenames(db, filenames: list[str]) -> dict[str, list[dict]]:
    if not filenames:
        return {}
    placeholders = ",".join("?" for _ in filenames)
    cursor = await db.execute(
        f"SELECT st.filename, t.name, t.color FROM source_tags st JOIN tags t ON st.tag_id = t.id WHERE st.filename IN ({placeholders})",
        filenames,
    )
    rows = await cursor.fetchall()
    result: dict[str, list[dict]] = {}
    for r in rows:
        result.setdefault(r["filename"], []).append({"name": r["name"], "color": r["color"]})
    return result


async def set_sources(sources: list[Source]) -> None:
    db = await get_db()
    try:
        await db.execute("DELETE FROM sources")
        for s in sources:
            await db.execute(
                "INSERT INTO sources (idx, filename, duration, resolution, codec, file_size) VALUES (?, ?, ?, ?, ?, ?)",
                (s.index, s.filename, s.duration, s.resolution, s.codec, s.file_size),
            )
        await db.commit()
    finally:
        await db.close()


async def next_assembly_id() -> str:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM assemblies ORDER BY created DESC LIMIT 1")
        row = await cursor.fetchone()
        if row:
            last_num = int(row["id"].split("_")[1])
            return f"asm_{last_num + 1:03d}"
        return "asm_001"
    finally:
        await db.close()


async def save_assembly(asm: Assembly) -> None:
    db = await get_db()
    try:
        await db.execute(
            """INSERT OR REPLACE INTO assemblies (id, name, status, error, preview, output_url, duration, note, created)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (asm.id, asm.name, asm.status, asm.error, int(asm.preview), asm.output_url, asm.duration, asm.note,
             asm.created),
        )
        await db.execute("DELETE FROM clips WHERE assembly_id = ?", (asm.id,))
        for clip in asm.clips:
            await db.execute(
                "INSERT INTO clips (assembly_id, pos, filename, start, end, duration) VALUES (?, ?, ?, ?, ?, ?)",
                (asm.id, clip.pos, clip.filename, clip.start, clip.end, clip.duration),
            )
        await db.commit()
    finally:
        await db.close()


async def get_assembly(assembly_id: str) -> Assembly | None:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM assemblies WHERE id = ?", (assembly_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        clips = await _fetch_clips(db, assembly_id)
        return Assembly(
            id=row["id"], name=row["name"], status=row["status"], error=row["error"],
            preview=bool(row["preview"]), output_url=row["output_url"],
            duration=row["duration"], note=row["note"], created=row["created"], clips=clips,
        )
    finally:
        await db.close()


async def delete_assembly(assembly_id: str) -> bool:
    db = await get_db()
    try:
        await db.execute("DELETE FROM clips WHERE assembly_id = ?", (assembly_id,))
        cursor = await db.execute("DELETE FROM assemblies WHERE id = ?", (assembly_id,))
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


async def update_assembly_note(assembly_id: str, note: str | None) -> bool:
    db = await get_db()
    try:
        cursor = await db.execute("UPDATE assemblies SET note = ? WHERE id = ?", (note, assembly_id))
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


async def list_assemblies() -> list[Assembly]:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM assemblies ORDER BY created DESC")
        rows = await cursor.fetchall()
        result = []
        for row in rows:
            clips = await _fetch_clips(db, row["id"])
            result.append(Assembly(
                id=row["id"], name=row["name"], status=row["status"], error=row["error"],
                preview=bool(row["preview"]), output_url=row["output_url"],
                duration=row["duration"], note=row["note"], created=row["created"], clips=clips,
            ))
        return result
    finally:
        await db.close()


async def list_tags() -> list[Tag]:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id, name, color FROM tags ORDER BY name")
        rows = await cursor.fetchall()
        return [Tag(id=r["id"], name=r["name"], color=r["color"]) for r in rows]
    finally:
        await db.close()


async def create_tag(name: str, color: str = "#839496") -> Tag | None:
    db = await get_db()
    try:
        try:
            cursor = await db.execute("INSERT INTO tags (name, color) VALUES (?, ?)", (name, color))
            await db.commit()
            return Tag(id=cursor.lastrowid, name=name, color=color)
        except Exception:
            return None
    finally:
        await db.close()


async def rename_tag(tag_id: int, name: str) -> Tag | None:
    db = await get_db()
    try:
        cursor = await db.execute("UPDATE tags SET name = ? WHERE id = ?", (name, tag_id))
        await db.commit()
        if cursor.rowcount == 0:
            return None
        cur2 = await db.execute("SELECT color FROM tags WHERE id = ?", (tag_id,))
        row = await cur2.fetchone()
        return Tag(id=tag_id, name=name, color=row["color"])
    finally:
        await db.close()


async def delete_tag(tag_id: int) -> bool:
    db = await get_db()
    try:
        await db.execute("PRAGMA foreign_keys = ON")
        cursor = await db.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


async def set_source_tags(filename: str, tag_ids: list[int]) -> None:
    db = await get_db()
    try:
        await db.execute("DELETE FROM source_tags WHERE filename = ?", (filename,))
        for tid in tag_ids:
            await db.execute("INSERT INTO source_tags (filename, tag_id) VALUES (?, ?)", (filename, tid))
        await db.commit()
    finally:
        await db.close()


async def _fetch_clips(db, assembly_id: str) -> list[ClipDetail]:
    cursor = await db.execute(
        "SELECT pos, filename, start, end, duration FROM clips WHERE assembly_id = ? ORDER BY pos", (assembly_id,)
    )
    rows = await cursor.fetchall()
    return [ClipDetail(pos=r["pos"], filename=r["filename"], start=r["start"], end=r["end"], duration=r["duration"])
            for r in rows]
