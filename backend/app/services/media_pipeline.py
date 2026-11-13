"""Background processing of image / audio / video uploads into audience records (multimodal ingestion)."""
import logging
import tempfile
from pathlib import Path
from typing import List

from app.services import gemini_service, media_service, source_service, whisper_service

log = logging.getLogger("media")


def _transcript_records(chunks: List[str], modality: str, label: str) -> List[dict]:
    return [{"source_id": f"{label}#{i}", "text": c, "timestamp": None, "likes": 0, "replies": 0, "platform": "upload",
             "author": None, "modality": modality} for i, c in enumerate(chunks)]


def process_image(sid: str, data: bytes, mime: str, name: str) -> dict:
    a = gemini_service.analyze_image(data, mime)           # raises GeminiError (handled by caller)
    text = ". ".join(x for x in [a.topic, a.pain_point, a.visible_text] if x)
    rec = {"source_id": name, "text": text, "timestamp": None, "likes": 0, "replies": 0, "platform": "upload", "author": None,
           "modality": "image", "ai": {"topic": a.topic, "intent": a.intent, "pain_point": a.pain_point, "sentiment": a.sentiment}}
    result = a.model_dump()
    source_service.attach_records(sid, [rec], {"file": name, "result": result})
    return result


def process_audio_file(sid: str, path: str, name: str, modality: str = "audio") -> dict:
    t = whisper_service.transcribe(path)
    chunks = media_service.chunk_transcript(t["text"])
    result = {"transcript": t["text"], "language": t["language"], "whisper_model": t["model"], "segments": len(chunks)}
    if gemini_service.is_configured():
        try:
            result["analysis"] = gemini_service.analyze_text(t["text"]).model_dump()
        except gemini_service.GeminiError as exc:
            result["analysis_unavailable"] = str(exc)
    else:
        result["analysis_unavailable"] = "Gemini not configured - transcript embedded and analysed with local models only"
    source_service.attach_records(sid, _transcript_records(chunks, modality, name), {"file": name, "result": result})
    return result


def process_video_file(sid: str, path: str, name: str) -> dict:
    with tempfile.TemporaryDirectory() as d:
        wav = str(Path(d) / "audio.wav")
        media_service.extract_audio(path, wav)
        t = whisper_service.transcribe(wav)
    chunks = media_service.chunk_transcript(t["text"])
    records = _transcript_records(chunks, "video", name)
    result = {"transcript": t["text"], "language": t["language"], "whisper_model": t["model"], "segments": len(chunks)}
    if gemini_service.is_configured():
        try:
            frames = media_service.extract_frames(path, 6)
            fa = gemini_service.analyze_frames(frames, t["text"])
            result["visual"] = fa.model_dump()
            records.append({"source_id": f"{name}#visual", "text": ". ".join(fa.visual_topics + [fa.visible_text, fa.context]).strip(". "),
                            "timestamp": None, "likes": 0, "replies": 0, "platform": "upload", "author": None, "modality": "video"})
        except (gemini_service.GeminiError, media_service.MediaError) as exc:
            result["visual_unavailable"] = str(exc)
    else:
        result["visual_unavailable"] = "Gemini not configured - frames not analysed"
    source_service.attach_records(sid, records, {"file": name, "result": result})
    return result


def run_background(sid: str, kind: str, path: str, name: str) -> None:
    try:
        (process_video_file if kind == "video" else process_audio_file)(sid, path, name)
    except (whisper_service.WhisperUnavailable, media_service.MediaError, gemini_service.GeminiError) as exc:
        source_service.fail_source(sid, str(exc))
    except Exception:
        log.exception("media processing failed")
        source_service.fail_source(sid, "The file could not be processed.")
    finally:
        Path(path).unlink(missing_ok=True)
