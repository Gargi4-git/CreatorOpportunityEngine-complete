"""All ingestion endpoints: CSV, YouTube, Reddit, image, audio, video, demo dataset, and source listing."""
import re
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.config import settings
from app.db.mongodb import DatabaseUnavailable, get_db
from app.services import (gemini_service, media_pipeline, media_service, reddit_service, source_service,
                          whisper_service, youtube_service)
from app.services.csv_service import CSVError, parse_csv
from app.services.progress import create_analysis
from app.services.pipeline_service import run_analysis

router = APIRouter(prefix="/api/sources", tags=["Sources"])
DEMO_CSV = Path(__file__).resolve().parent.parent / "demo" / "demo_comments.csv"


def _db():
    try:
        return get_db()
    except DatabaseUnavailable as exc:
        raise HTTPException(503, str(exc))


def _safe_name(name: Optional[str], default: str) -> str:
    return re.sub(r"[^\w.\- ]", "_", name or default)[:120]


async def _read_limited(file: UploadFile, mb: int) -> bytes:
    raw = await file.read(mb * 1024 * 1024 + 1)
    if len(raw) > mb * 1024 * 1024:
        raise HTTPException(413, f"File too large. Maximum size is {mb} MB.")
    if not raw:
        raise HTTPException(422, "The uploaded file is empty.")
    return raw


def _start(background: BackgroundTasks, sid: str) -> str:
    aid = create_analysis([sid])
    background.add_task(run_analysis, aid)
    return aid


# ------------------------------------------------------------------ CSV
@router.post("/csv/upload")
async def upload_csv(file: UploadFile = File(...)):
    """Validate + store a CSV. Returns the detection report; analysis starts via POST /api/analysis/run."""
    name = _safe_name(file.filename, "upload.csv")
    if not name.lower().endswith(".csv"):
        raise HTTPException(400, "Unsupported file type. Please upload a .csv file.")
    raw = await _read_limited(file, settings.max_upload_mb)
    try:
        records, report = parse_csv(raw)
    except CSVError as exc:
        raise HTTPException(422, str(exc))
    _db()
    sid = source_service.create_source("csv", name, records, {"report": report})
    return {"source_id": sid, "file_name": name, **report}


# ------------------------------------------------------------------ YouTube
class YouTubeRequest(BaseModel):
    url: str = Field(max_length=300)
    comment_limit: int = Field(250, ge=10, le=1000)


@router.post("/youtube/analyze")
def youtube_analyze(req: YouTubeRequest, background: BackgroundTasks):
    _db()
    try:
        vid = youtube_service.extract_video_id(req.url)
        if not settings.youtube_configured:
            raise youtube_service.YouTubeNotConfigured()
        meta = youtube_service.fetch_metadata(vid)
        records = youtube_service.fetch_comments(vid, req.comment_limit)
    except youtube_service.YouTubeNotConfigured as exc:
        raise HTTPException(503, {"code": "api_key_required", "message": str(exc)})
    except youtube_service.YouTubeError as exc:
        raise HTTPException(422, str(exc))
    sid = source_service.create_source("youtube", meta["title"] or vid, records, {"video": meta})
    return {"source_id": sid, "analysis_id": _start(background, sid), "video": meta, "comments_fetched": len(records)}


# ------------------------------------------------------------------ Reddit
class RedditRequest(BaseModel):
    target: str = Field(max_length=300, description="post URL, subreddit URL, or r/name")
    limit: int = Field(100, ge=10, le=500)


@router.post("/reddit/analyze")
def reddit_analyze(req: RedditRequest, background: BackgroundTasks):
    _db()
    try:
        reddit_service.parse_target(req.target)
        records, meta = reddit_service.fetch(req.target, req.limit)
    except reddit_service.RedditNotConfigured as exc:
        raise HTTPException(503, {"code": "api_key_required", "message": str(exc)})
    except reddit_service.RedditError as exc:
        raise HTTPException(422, str(exc))
    label = f"r/{meta['subreddit']}" + (f" post {meta['post_id']}" if meta["post_id"] else "")
    sid = source_service.create_source("reddit", label, records, meta)
    return {"source_id": sid, "analysis_id": _start(background, sid), "records_fetched": len(records), **meta}


# ------------------------------------------------------------------ Demo dataset (clearly labelled; runs the SAME pipeline)
@router.post("/demo/load")
def demo_load(background: BackgroundTasks):
    _db()
    records, report = parse_csv(DEMO_CSV.read_bytes(), default_platform="csv")
    sid = source_service.create_source("csv", "Demo Dataset (synthetic sample)", records, {"report": report}, dataset_label="demo")
    return {"source_id": sid, "analysis_id": _start(background, sid), "dataset_label": "demo", "rows": len(records)}


# ------------------------------------------------------------------ Images
@router.post("/image/analyze")
async def image_analyze(file: UploadFile = File(...)):
    name = _safe_name(file.filename, "image")
    ext = Path(name).suffix.lower()
    if ext not in media_service.IMAGE_EXT:
        raise HTTPException(400, "Unsupported image type. Use PNG, JPG, JPEG or WEBP.")
    data = await _read_limited(file, 10)
    if not media_service.check_magic(ext, data[:32]):
        raise HTTPException(400, "The file content does not match its extension.")
    _db()
    sid = source_service.create_source("image", name, [], status="processing")
    try:
        result = media_pipeline.process_image(sid, data, media_service.IMAGE_EXT[ext], name)
    except gemini_service.GeminiError as exc:
        source_service.fail_source(sid, str(exc))
        raise HTTPException(503 if isinstance(exc, gemini_service.GeminiNotConfigured) else 502, str(exc))
    return {"source_id": sid, "status": "ready", "result": result}


# ------------------------------------------------------------------ Audio / video (background)
async def _media_upload(file: UploadFile, background: BackgroundTasks, kind: str):
    exts = media_service.AUDIO_EXT if kind == "audio" else media_service.VIDEO_EXT
    name = _safe_name(file.filename, kind)
    ext = Path(name).suffix.lower()
    if ext not in exts:
        raise HTTPException(400, f"Unsupported {kind} type. Use " + ", ".join(sorted(e.upper().lstrip('.') for e in exts)) + ".")
    data = await _read_limited(file, 25 if kind == "audio" else 100)
    if not media_service.check_magic(ext, data[:32]):
        raise HTTPException(400, "The file content does not match its extension.")
    if not whisper_service.available():
        raise HTTPException(503, "Audio transcription unavailable: install openai-whisper (and ffmpeg) on the server.")
    _db()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext, dir=tempfile.gettempdir())
    tmp.write(data); tmp.close()
    sid = source_service.create_source(kind, name, [], status="processing")
    background.add_task(media_pipeline.run_background, sid, kind, tmp.name, name)
    return {"source_id": sid, "status": "processing"}


@router.post("/audio/analyze")
async def audio_analyze(background: BackgroundTasks, file: UploadFile = File(...)):
    return await _media_upload(file, background, "audio")


@router.post("/video/analyze")
async def video_analyze(background: BackgroundTasks, file: UploadFile = File(...)):
    return await _media_upload(file, background, "video")


# ------------------------------------------------------------------ listing
@router.get("")
def list_sources():
    db = _db()
    out = []
    for s in db.sources.find({}).sort("created_at", -1).limit(100):
        last = db.analyses.find_one({"source_ids": s["_id"], "status": "completed"}, sort=[("completed_at", -1)])
        out.append({"id": s["_id"], "type": s["type"], "label": s["label"], "dataset_label": s["dataset_label"],
                    "status": s["status"], "error": s.get("error"), "records": s.get("record_count", 0),
                    "created_at": s["created_at"], "last_analyzed": last["completed_at"] if last else None})
    return {"sources": out}


@router.get("/{source_id}")
def get_source(source_id: str):
    s = _db().sources.find_one({"_id": source_id})
    if not s:
        raise HTTPException(404, "Source not found.")
    s["id"] = s.pop("_id")
    return s
