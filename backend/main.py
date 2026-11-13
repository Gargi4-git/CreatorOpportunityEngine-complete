from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.routes.analysis import router as analysis_router
from backend.api.routes.creator_studio import router as creator_router
from backend.api.routes.video import router as video_router


app = FastAPI(
    title="Creator Opportunity Engine",
    description="AI-powered audience intelligence platform for creators",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MEDIA_DIR = Path("data/generated")
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")

app.include_router(
    analysis_router
)
app.include_router(
    creator_router
)
app.include_router(
    video_router
)


@app.get("/")
def root():
    return {
        "message": "Creator Opportunity Engine is running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }