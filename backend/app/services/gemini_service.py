"""
Gemini access (backend only; the key never reaches the frontend).
Every call asks for JSON and validates it with Pydantic. On failure a GeminiError (human-readable) is raised -
we never silently substitute canned content.
"""
import json
import logging
import os
from typing import List, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

from app.config import settings
from app.models.analysis import (ClusterSummary, ContentBrief, FrameAnalysis, ImageAnalysis, Recommendation,
                                 TextAnalysis, TopicLabel)

log = logging.getLogger("gemini")
T = TypeVar("T", bound=BaseModel)

MODELS = [m.strip() for m in os.getenv("GEMINI_MODELS", "gemini-3.5-flash-lite,gemini-3.1-flash-lite,gemini-flash-latest").split(",") if m.strip()]


class GeminiError(RuntimeError):
    """Safe to show to the user."""


class GeminiNotConfigured(GeminiError):
    def __init__(self):
        super().__init__("Gemini not configured. Add GEMINI_API_KEY to your .env file.")


_client = None


def _get_client():
    global _client
    if _client is None and not settings.gemini_configured:
        raise GeminiNotConfigured()
    if _client is None:
        try:
            from google import genai
            _client = genai.Client(api_key=settings.gemini_api_key)
        except Exception as exc:
            raise GeminiError("The Gemini client could not be initialised. Check the google-genai package.") from exc
    return _client


def is_configured() -> bool:
    return _client is not None or settings.gemini_configured


def set_client(c) -> None:
    """Injection point (tests)."""
    global _client
    _client = c


def _call(prompt: str, schema: Type[T], parts: Optional[list] = None) -> T:
    client = _get_client()
    from google.genai import types
    contents = (parts or []) + [prompt]
    last: Optional[Exception] = None
    for model in MODELS:
        for attempt in range(2):  # one retry with a stricter reminder if JSON is invalid
            try:
                p = contents if attempt == 0 else contents[:-1] + [prompt + "\n\nReturn ONLY valid JSON matching the schema."]
                resp = client.models.generate_content(
                    model=model, contents=p,
                    config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.3))
                data = json.loads(resp.text)
                return schema.model_validate(data)
            except (json.JSONDecodeError, ValidationError, TypeError) as exc:
                last = exc
                continue
            except Exception as exc:  # quota, model not found, network...
                last = exc
                log.warning("gemini model %s failed: %s", model, type(exc).__name__)
                break
    msg = str(last).lower() if last else ""
    if "quota" in msg or "429" in msg or "resource_exhausted" in msg:
        raise GeminiError("Gemini quota exceeded. Try again later.")
    if isinstance(last, (json.JSONDecodeError, ValidationError)):
        raise GeminiError("Gemini returned an invalid response. Please retry.")
    raise GeminiError("Gemini request failed. Check your API key and network connection.")


def _schema_hint(schema: Type[BaseModel]) -> str:
    return json.dumps(schema.model_json_schema().get("properties", {}), indent=1)


def analyze_text(text: str) -> TextAnalysis:
    return _call(f"""Analyze this audience message for a content creator. Respond with JSON matching:
{_schema_hint(TextAnalysis)}
intent is one of: question, complaint, request, recommendation, confusion, learning_request, feature_request, career_request, comparison, tutorial_request.
Message: \"\"\"{text[:2000]}\"\"\"""", TextAnalysis)


def analyze_image(image_bytes: bytes, mime_type: str) -> ImageAnalysis:
    from google.genai import types
    part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    return _call(f"""This image is a screenshot related to a creator's audience (a comment, question, error message, poll, analytics...).
Extract what is actually visible; do not invent text. Respond with JSON matching:
{_schema_hint(ImageAnalysis)}""", ImageAnalysis, [part])


def analyze_frames(frames: List[bytes], transcript_excerpt: str = "") -> FrameAnalysis:
    from google.genai import types
    parts = [types.Part.from_bytes(data=f, mime_type="image/jpeg") for f in frames]
    return _call(f"""These are representative frames from a video. Transcript excerpt (may be empty): \"\"\"{transcript_excerpt[:1500]}\"\"\"
Describe the visual topics shown. Respond with JSON matching:
{_schema_hint(FrameAnalysis)}""", FrameAnalysis, parts)


def label_topic(sample_comments: List[str], keyword_label: str) -> TopicLabel:
    joined = "\n".join(f"- {c[:200]}" for c in sample_comments[:12])
    return _call(f"""Name the shared audience need in these comments. Base the label ONLY on the comments.
Keyword hint: {keyword_label}
Comments:
{joined}
Respond with JSON matching:
{_schema_hint(TopicLabel)}
label: a short human-readable topic (max 6 words). search_query: a YouTube search query that finds existing content on this topic.""", TopicLabel)


def summarize_cluster(sample_comments: List[str]) -> ClusterSummary:
    joined = "\n".join(f"- {c[:200]}" for c in sample_comments[:15])
    return _call(f"Summarize what this group of audience comments is about, using only the comments.\n{joined}\n"
                 f"Respond with JSON matching:\n{_schema_hint(ClusterSummary)}", ClusterSummary)


def _evidence_block(evidence: List[dict]) -> str:
    return "\n".join(f'[{e["id"]}] ({e["platform"]}, {e["likes"]} likes) {e["text"][:260]}' for e in evidence)


def generate_recommendation(opportunity: dict, evidence: List[dict]) -> Recommendation:
    s = opportunity["scores"]
    unavailable = ", ".join(opportunity.get("unavailable_components") or []) or "none"
    prompt = f"""You are the recommendation agent of a Creator Opportunity Engine. Recommend ONE piece of content.
Use ONLY the evidence below. Do not invent statistics or quotes. Cite supporting comments by their [id] in evidence_ids.

TOPIC: {opportunity["topic"]}
EVIDENCE COUNT: {opportunity["evidence_count"]} audience comments in this cluster
SCORES (0-100): GhostGap={s["ghostgap"]} Demand={s["demand"]} Trend={s["trend"]} Pain={s["pain"]} Engagement={s["engagement"]} Freshness={s["freshness"]} Competition={s["competition"]}
UNAVAILABLE SIGNALS (do not claim anything about these): {unavailable}
PLATFORM SHARE %: {opportunity["platform_share"]}
INTENTS: {opportunity["intent_distribution"]}
REPRESENTATIVE AUDIENCE COMMENTS:
{_evidence_block(evidence)}

Respond with JSON matching:
{_schema_hint(Recommendation)}"""
    return _call(prompt, Recommendation)


def generate_content_brief(opportunity: dict, evidence: List[dict], content_format: str) -> ContentBrief:
    s = opportunity["scores"]
    rec = opportunity.get("recommendation") or {}
    prompt = f"""Write a content brief for a creator. Format: {content_format}.
Ground it ONLY in this audience evidence; cite comment [id]s you rely on in evidence_ids.

TOPIC: {opportunity["topic"]}  (GhostGap {s["ghostgap"]}, Demand {s["demand"]}, Pain {s["pain"]})
PRIOR RECOMMENDATION: {json.dumps(rec)[:800]}
EVIDENCE:
{_evidence_block(evidence)}

Respond with JSON matching:
{_schema_hint(ContentBrief)}
script: a complete script or post body appropriate for the format. outline: ordered section titles."""
    return _call(prompt, ContentBrief)
