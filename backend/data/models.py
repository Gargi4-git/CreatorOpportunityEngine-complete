from pydantic import BaseModel
from typing import Optional


class AudienceComment(BaseModel):
    id: str
    source: str
    author: str
    text: str
    timestamp: str
    engagement: int = 0
    url: Optional[str] = None
    