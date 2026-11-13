from pathlib import Path
from typing import Optional
from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.video.generator import create_video_from_opportunity


router = APIRouter(
    prefix="/video",
    tags=["Video Generation"]
)


VIDEO_FILE = Path("data/generated/creator_video.mp4")


class VideoRequest(BaseModel):
    video_format: Optional[str] = "youtube"
    format: Optional[str] = None


@router.post("/generate")
def generate_video(payload: Optional[VideoRequest] = None):
    chosen_format = "youtube"
    if payload:
        chosen_format = payload.format or payload.video_format or "youtube"

    if chosen_format not in {"youtube", "shorts"}:
        return {
            "status": "error",
            "message": "video_format must be 'youtube' or 'shorts'"
        }

    result = create_video_from_opportunity(video_format=chosen_format)

    return {
        "status": "success",
        "video_url": "/video/file",
        "video_format": result.get("video_format", chosen_format),
        "opportunity_score": result["opportunity_score"],
        "audience_problem": result["audience_problem"],
        "scene_count": result["scene_count"],
        "scenes": result.get("scenes", []),
    }


@router.get("/file")
def get_video():
    if not VIDEO_FILE.exists():
        fallback_file = Path("data/generated/demo_pipeline_video.mp4")
        if fallback_file.exists():
            return FileResponse(
                path=fallback_file,
                media_type="video/mp4",
                filename="creator_video.mp4"
            )
        return {"error": "No generated video found."}

    return FileResponse(
        path=VIDEO_FILE,
        media_type="video/mp4",
        filename="creator_video.mp4"
    )
