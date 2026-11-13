"""Speech-to-text with OpenAI Whisper (local). Lazy import: the app runs without it and reports it as unavailable."""
import os

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
_model = None


class WhisperUnavailable(RuntimeError):
    pass


def available() -> bool:
    if _model is not None:
        return True
    try:
        import whisper  # noqa: F401
        return True
    except Exception:
        return False


def set_model(m) -> None:
    global _model
    _model = m


def transcribe(path: str) -> dict:
    global _model
    if _model is None:
        try:
            import whisper
            _model = whisper.load_model(WHISPER_MODEL)
        except Exception as exc:
            raise WhisperUnavailable("Audio transcription unavailable: install openai-whisper (and ffmpeg).") from exc
    try:
        res = _model.transcribe(path, fp16=False)
    except Exception as exc:
        raise WhisperUnavailable("The audio could not be transcribed. The file may be corrupt or unsupported.") from exc
    text = (res.get("text") or "").strip()
    if not text:
        raise WhisperUnavailable("No speech was detected in this file.")
    return {"text": text, "language": res.get("language"), "model": WHISPER_MODEL}
