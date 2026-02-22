from pathlib import Path

SOURCES_DIR = Path("./sources")
MEDIA_DIR = Path("./media")
DATA_DIR = Path("./data")
DB_PATH = DATA_DIR / "kalinsky.db"
PREVIEWS_DIR = MEDIA_DIR / "previews"
FFMPEG_BIN = "ffmpeg"
FFPROBE_BIN = "ffprobe"
AUDIO_FADE_MS = 50
AUDIO_CODEC = "aac"
AUDIO_BITRATE = "128k"
