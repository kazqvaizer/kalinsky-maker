from pathlib import Path

from app import state
from app.config import MEDIA_DIR
from app.models.assembly import Assembly
from app.services.concat import concat_segments
from app.services.cutter import cut_segment
from app.services.probe import probe_video


async def run_assembly(asm: Assembly) -> None:
    try:
        asm_dir = MEDIA_DIR / asm.id
        seg_dir = asm_dir / "segments"
        seg_dir.mkdir(parents=True, exist_ok=True)

        segment_paths: list[Path] = []

        seg_ext = ".ts" if asm.preview else ".mp4"
        for clip in asm.clips:
            seg_path = seg_dir / f"{clip.pos:03d}{seg_ext}"
            await cut_segment(
                filename=clip.filename,
                start=clip.start,
                end=clip.end,
                output_path=seg_path,
                preview=asm.preview,
                pos=clip.pos,
            )
            segment_paths.append(seg_path)

        result_path = asm_dir / "result.mp4"
        await concat_segments(segment_paths, result_path)

        info = await probe_video(str(result_path))

        asm.status = "done"
        asm.duration = info["duration"]
        asm.output_url = f"/media/{asm.id}/result.mp4"
    except Exception as e:
        asm.status = "failed"
        asm.error = str(e)
    finally:
        await state.save_assembly(asm)
