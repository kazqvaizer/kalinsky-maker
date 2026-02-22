# Kalinsky Maker

Video assembly service — browse source videos, trim and reorder clips, preview with timecode overlay, produce clean outputs.

Built with FastAPI, FFmpeg, SQLite, and vanilla JS.

## Quick Start

```bash
docker compose up --build
```

Open http://localhost in your browser.

## Setup

1. Place source video files (`.mp4`, `.mov`, `.mkv`, `.webm`) into the `sources/` directory
2. Click **Reindex** in the UI to scan sources
3. Click sources to add clips, adjust trim points, hit **Assemble**

## Features

- Trim and reorder clips from multiple source videos
- Preview mode with timecode overlay (stream-copy for clean releases)
- Tag sources for organization (survives reindex)
- Results split into Tries (previews) and Releases tabs
- Audio fade in/out at trim boundaries
- Background FFmpeg processing with live status updates

## Dev

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## License

MIT
