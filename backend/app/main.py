from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analysis, analytics, creator_studio, health, opportunities, search, upload
from app.config import settings

app = FastAPI(title="Creator Opportunity Engine API", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins), allow_methods=["*"], allow_headers=["*"])
for r in (health.router, upload.router, analysis.router, opportunities.router, analytics.router, creator_studio.router, search.router):
    app.include_router(r)
