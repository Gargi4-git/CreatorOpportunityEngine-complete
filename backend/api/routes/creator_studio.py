from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel

from backend.ai.creator_studio import (
    load_best_opportunity,
    generate_next_video,
    generate_video_ideas,
    generate_title_ideas,
    generate_video_outline,
    generate_video_script,
    generate_content_calendar,
    creator_chat,
)
from backend.video.pipeline import generate_complete_opportunity_video


router = APIRouter(
    prefix="/creator",
    tags=["Creator Studio"]
)


class ChatRequest(BaseModel):
    question: str


@router.get("/best-opportunity")
def best_opportunity():
    return load_best_opportunity()


@router.post("/next-video")
def next_video():
    return {
        "result": generate_next_video()
    }


@router.post("/ideas")
def video_ideas():
    return {
        "result": generate_video_ideas(10)
    }


@router.post("/titles")
def titles():
    return {
        "result": generate_title_ideas()
    }


@router.post("/outline")
def outline():
    return {
        "result": generate_video_outline()
    }


@router.post("/script")
def script():
    return {
        "result": generate_video_script()
    }


@router.post("/calendar")
def calendar():
    return {
        "result": generate_content_calendar(7)
    }


@router.post("/chat")
def chat(request: ChatRequest):
    return {
        "question": request.question,
        "result": creator_chat(request.question)
    }


@router.post("/generate-video")
def generate_video_endpoint():
    """
    Generate an actual MP4 video with visual scene cards and AI voice narration
    from the highest-ranked audience opportunity.
    """
    res = generate_complete_opportunity_video(output_filename="creator_video.mp4")
    return res


@router.get("/latest-video")
def get_latest_video():
    video_file = Path("data/generated/creator_video.mp4")
    if not video_file.exists():
        video_file = Path("data/generated/demo_pipeline_video.mp4")
    if not video_file.exists():
        video_file = Path("data/generated/test_creator_video.mp4")

    if video_file.exists():
        return {
            "available": True,
            "filename": video_file.name,
            "video_url": f"http://127.0.0.1:8000/media/{video_file.name}",
            "size_kb": round(video_file.stat().st_size / 1024, 1),
        }
    return {
        "available": False,
        "message": "No generated video found. Click Generate MP4 Video to create one.",
    }


class AnalyzeAudienceRequest(BaseModel):
    source: str = "youtube"
    url: str
    max_comments: int = 250


@router.post("/analyze-audience")
def analyze_audience_endpoint(request: AnalyzeAudienceRequest):
    """
    Ingest real audience comments from a YouTube video URL,
    run the full analysis, clustering, and Gemini recommendation pipeline,
    and return the updated top opportunity.
    """
    if request.source == "youtube":
        from backend.data.youtube_collector import collect_comments
        from backend.pipeline import run_pipeline

        try:
            # 1. Collect comments
            df = collect_comments(request.url, max_comments=request.max_comments)

            # 2. Run the end-to-end intelligence pipeline
            run_pipeline()

            # 3. Load the updated top opportunity
            best = load_best_opportunity()

            return {
                "status": "success",
                "source": "youtube",
                "comments_collected": len(df),
                "best_opportunity": best,
                "message": f"Successfully ingested {len(df)} YouTube comments and synthesized new content opportunities!",
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
            }
    else:
        return {
            "status": "error",
            "message": f"Source '{request.source}' is not supported yet.",
        }

