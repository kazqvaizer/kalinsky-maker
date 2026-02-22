import aiosqlite

from app.config import DATA_DIR, DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    idx INTEGER NOT NULL,
    filename TEXT NOT NULL,
    duration REAL NOT NULL,
    resolution TEXT NOT NULL,
    codec TEXT NOT NULL,
    file_size INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS assemblies (
    id TEXT PRIMARY KEY,
    name TEXT,
    status TEXT NOT NULL,
    error TEXT,
    preview INTEGER NOT NULL DEFAULT 1,
    output_url TEXT,
    duration REAL,
    note TEXT,
    created TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    color TEXT NOT NULL DEFAULT '#839496'
);

CREATE TABLE IF NOT EXISTS source_tags (
    filename TEXT NOT NULL,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (filename, tag_id)
);

CREATE TABLE IF NOT EXISTS clips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assembly_id TEXT NOT NULL,
    pos INTEGER NOT NULL,
    filename TEXT NOT NULL,
    start REAL NOT NULL,
    end REAL NOT NULL,
    duration REAL NOT NULL,
    FOREIGN KEY (assembly_id) REFERENCES assemblies(id)
);
"""


MIGRATIONS = [
    "ALTER TABLE assemblies ADD COLUMN note TEXT",
    "ALTER TABLE tags ADD COLUMN color TEXT NOT NULL DEFAULT '#839496'",
]


async def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        for sql in MIGRATIONS:
            try:
                await db.execute(sql)
            except Exception:
                pass  # column already exists
        await db.commit()


async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


if __name__ == "__main__":
    import asyncio
    asyncio.run(init_db())
    print(f"Database initialized at {DB_PATH}")
