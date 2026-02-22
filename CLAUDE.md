# Kalinsky API — FFmpeg Video Assembly Service

FastAPI REST API: browse source videos, assemble clips (trim/reorder), preview with timecode overlay, produce clean outputs. No auth. Assemblies are immutable.

## Tech

Python 3.11+ / uv / FastAPI + uvicorn / ffmpeg via `asyncio.create_subprocess_exec` / SQLite via aiosqlite / nginx for output serving (FastAPI fallback in dev)

## Layout

```
├── docker-compose.yml          # full stack (nginx + api)
├── CLAUDE.md
├── backend/                    # API service
│   ├── Dockerfile
│   ├── entrypoint.sh
│   ├── pyproject.toml
│   ├── uv.lock
│   └── app/
│       ├── main.py             # FastAPI app, lifespan, CORS
│       ├── config.py           # settings (paths, defaults)
│       ├── db.py               # SQLite init, schema, connection helper
│       ├── state.py            # async DB-backed state functions
│       ├── routers/
│       │   ├── sources.py      # /api/v1/sources
│       │   └── assemblies.py   # /api/v1/assemblies
│       ├── services/
│       │   ├── probe.py        # ffprobe wrapper
│       │   ├── cutter.py       # segment cutting (preview + clean)
│       │   ├── concat.py       # concatenation
│       │   └── assembly.py     # assembly orchestration
│       └── models/
│           ├── source.py       # Source pydantic models
│           └── assembly.py     # Assembly pydantic models
├── frontend/                   # static HTML/JS served by nginx
├── nginx/nginx.conf            # nginx configuration
├── sources/                    # source video files (read-only)
├── output/                     # generated files (nginx-served)
└── data/                       # SQLite database
```

## Docker Architecture

### Containers

| Service | Image | Role |
|---|---|---|
| `nginx` | nginx:alpine | Reverse proxy, static frontend, output file serving |
| `api` | Dockerfile (custom) | FastAPI + ffmpeg |

### Dockerfile (API)

In `backend/`. Base: python:3.11-slim. Install ffmpeg, uv. Copy app, `uv sync --no-dev`. Run uvicorn on port 8000. Mount `sources/` and `output/` as volumes.

### docker-compose.yml

- **nginx**: ports 80:80, mounts `frontend/` → `/usr/share/nginx/html`, mounts `output/` → `/output` (read-only), mounts `nginx/nginx.conf` → `/etc/nginx/nginx.conf`, depends_on api
- **api**: build from `backend/` Dockerfile, no published ports (internal only), mounts `sources/`, `output/`, and `data/` as volumes

### nginx.conf routing

| Location | Target |
|---|---|
| `/` | Static files from `frontend/` (index.html, JS, CSS) |
| `/api/` | `proxy_pass http://api:8000` (upstream to FastAPI) |
| `/output/` | Direct file serving from output volume (efficient, bypasses API) |

### Frontend (`frontend/`)

Static HTML + vanilla JS (no build step). Calls `/api/v1/...` endpoints. Files: `index.html`, `app.js`, `style.css`.

### Shared volumes

`sources/`, `output/`, and `data/` are bind-mounted into the API container. `output/` is also mounted read-only into nginx. API writes to `output/` and `data/`, nginx reads from `output/`.

## Config (`config.py`)

SOURCES_DIR=`./sources`, OUTPUT_DIR=`./output`, DATA_DIR=`./data`, DB_PATH=`./data/kalinsky.db`, FFMPEG_BIN=`ffmpeg`, FFPROBE_BIN=`ffprobe`, AUDIO_FADE_MS=50, AUDIO_CODEC=`aac`, AUDIO_BITRATE=`128k`

## Models

**Source:** index(int, 1-based), filename(str), duration(float, sec), resolution(str, e.g. "1080x1920"), codec(str), file_size(int, bytes)

**ClipInput:** source(int|str, index or filename), start(float|None=0), end(float|None=full duration)

**AssemblyCreate:** name(str|None), clips(list[ClipInput]), preview(bool=True, timecode overlay)

**ClipDetail:** pos(int, 1-based), filename(str), start(float), end(float), duration(float)

**Assembly:** id(str, "asm_001"), name(str|None), status("processing"|"done"|"failed"), error(str|None), preview(bool), clips(list[ClipDetail]), output_url(str|None, "/output/asm_001/result.mp4"), duration(float|None), created(str, ISO 8601)

## API

| Endpoint | Method | Behavior |
|---|---|---|
| `/api/v1/sources/reindex` | POST | Sync ffprobe scan of `sources/` (*.mp4,*.mov,*.mkv,*.webm). Replaces index. → 200 `{status,count}` |
| `/api/v1/sources` | GET | Cached index → 200 list[Source]. 409 if not indexed |
| `/api/v1/assemblies` | POST | Create immutable assembly, background ffmpeg. → 202 Assembly |
| `/api/v1/assemblies` | GET | List all (newest first) → 200 list[Assembly] |
| `/api/v1/assemblies/{id}` | GET | Single assembly → 200 Assembly, 404 if missing |
| `/output/{asm_id}/{filename}` | GET | Static file serving (dev mode) |

**Validation (422):** source not found, start>=end, start/end exceeds duration, empty clips list

## FFmpeg Pipeline

1. **Cut segments** per clip:
   - `-ss {start} -to {end} -i sources/{filename}`
   - Video: stream copy (re-encode only if preview overlay)
   - Audio: always re-encode to AAC with fade in/out (AUDIO_FADE_MS) at trim boundaries
   - Preview: drawtext timecode overlay (forces video re-encode)
   - Output: `output/{asm_id}/segments/{pos:03d}.mp4`

2. **Concat** via concat demuxer (`-f concat -safe 0`) → `output/{asm_id}/result.mp4`

3. **Update state** → done/failed + output_url/duration/error

**Re-encode rules:** preview=true always re-encodes video. preview=false stream-copies video. Mismatched resolution/fps → re-encode all to first clip's params.

## Background Tasks

`asyncio.create_task` from endpoint handler. Store task ref in assembly state.

## Error Handling

| Case | HTTP | |
|---|---|---|
| Not indexed | 409 | `"No index. Call POST /sources/reindex first."` |
| Source not found | 422 | `"Source 99 not found"` |
| Invalid trim | 422 | `"start >= end for clip 2"` |
| Assembly not found | 404 | `"Assembly not found"` |
| ffmpeg crash | — | status→failed, stderr in error field |

## CORS

Allow all origins/methods/headers (single-user local app).

## Startup (lifespan)

Create `sources/`, `output/`, `data/` dirs if missing. Initialize SQLite database. Auto-reindex (optional, configurable).

## Dev Commands

```bash
cd backend
uv sync                # install deps
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000  # dev server
uv run pytest          # tests
uv add <pkg>           # add dependency
```

## pyproject.toml

name=kalinsky-api, version=0.1.0, python>=3.11, deps: fastapi>=0.115, uvicorn[standard]>=0.34, aiosqlite>=0.22. Dev: ruff, pytest, httpx, pytest-asyncio. Ruff: line-length=120, py311, select=E,F,I.

## Database (SQLite)

Tables: `sources` (idx, filename, duration, resolution, codec, file_size), `assemblies` (id PK, name, status, error, preview, output_url, duration, created), `clips` (assembly_id FK, pos, filename, start, end, duration). DB file: `data/kalinsky.db`. Schema applied via `app.db.init_db()` at startup and `python -m app.db` in Docker entrypoint.
