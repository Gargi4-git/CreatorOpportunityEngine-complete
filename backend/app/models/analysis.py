"""Pydantic schemas used to VALIDATE every structured LLM output."""
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

Sentiment = Literal["positive", "negative", "neutral"]


class TextAnalysis(BaseModel):
    topic: str
    intent: str
    pain_point: str
    sentiment: Sentiment
    confidence: float = Field(ge=0, le=1)


class ImageAnalysis(BaseModel):
    visible_text: str = ""
    topic: str
    intent: str
    pain_point: str
    sentiment: Sentiment
    entities: List[str] = []
    context: str = ""
    confidence: float = Field(ge=0, le=1)


class FrameAnalysis(BaseModel):
    visual_topics: List[str]
    visible_text: str = ""
    context: str = ""
    confidence: float = Field(ge=0, le=1)


class TopicLabel(BaseModel):
    label: str
    audience_need: str
    search_query: str
    confidence: float = Field(ge=0, le=1)


class ClusterSummary(BaseModel):
    summary: str
    main_pain_points: List[str]


class Recommendation(BaseModel):
    recommended_topic: str
    content_format: str
    title: str
    target_audience: str
    content_angle: str
    suggested_sections: List[str]
    cta: str
    expected_value: str
    reason: str
    evidence_ids: List[int] = Field(description="ids of the numbered audience comments that support this recommendation")
    confidence: float = Field(ge=0, le=1)


class ContentBrief(BaseModel):
    title: str
    hook: str
    target_audience: str
    format: str
    length: str
    outline: List[str]
    script: str
    cta: str
    evidence_ids: List[int] = []
