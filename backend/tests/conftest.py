"""TEST-ONLY stub embedder (hashing bag-of-words). Production uses sentence-transformers/all-MiniLM-L6-v2.
These tests verify pipeline mechanics, persistence and data-dependence - NOT semantic quality of MiniLM."""
import os
# Isolate tests from any real .env (python-dotenv never overrides variables that are already set, even to "").
for _k in ("GEMINI_API_KEY", "YOUTUBE_API_KEY", "REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT"):
    os.environ[_k] = ""

import mongomock
import numpy as np
import pytest
from fastapi.testclient import TestClient
from sklearn.feature_extraction.text import HashingVectorizer

from app.db import mongodb
from app.ml import embeddings


class HashEmbedder:
    name = "TEST-ONLY hashing embedder"
    _v = HashingVectorizer(n_features=384, alternate_sign=False, norm="l2", ngram_range=(1, 2), stop_words="english")

    def encode(self, texts):
        return np.asarray(self._v.transform(texts).todense(), dtype=np.float32)


@pytest.fixture()
def client():
    mongodb.set_db(mongomock.MongoClient()["test"])
    embeddings.set_embedder(HashEmbedder())
    from app.main import app
    yield TestClient(app)
    mongodb.set_db(None)
    embeddings.set_embedder(None)


# ---------------------------------------------------------------- mocks for external services (test-only)
import dataclasses
import json
from types import SimpleNamespace

from app import config as app_config
from app.services import gemini_service, whisper_service

PATCH_TARGETS = ["app.config", "app.api.upload", "app.services.youtube_service", "app.services.reddit_service",
                 "app.services.gemini_service", "app.agents.recommendation_agent"]


@pytest.fixture()
def configure(monkeypatch):
    """configure(youtube=True, reddit=True, gemini=True) -> flips credentials on in every module that reads settings."""
    import importlib

    def _apply(youtube=False, reddit=False, gemini=False):
        s = dataclasses.replace(
            app_config.settings, youtube_api_key="yt-key" if youtube else "",
            reddit_client_id="id" if reddit else "", reddit_client_secret="sec" if reddit else "",
            reddit_user_agent="ua" if reddit else "", gemini_api_key="gk" if gemini else "")
        for mod in PATCH_TARGETS:
            m = importlib.import_module(mod)
            if hasattr(m, "settings"):
                monkeypatch.setattr(m, "settings", s)
        if gemini:
            gemini_service.set_client(FakeGemini())
        return s
    yield _apply
    gemini_service.set_client(None)
    whisper_service.set_model(None)


class FakeGemini:
    """Test double for google-genai's client: returns schema-valid JSON chosen by prompt content."""
    def __init__(self, evidence_ids=(1, 2), image_topic="ML model deployment error"):
        self.evidence_ids, self.image_topic = list(evidence_ids), image_topic
        self.models = SimpleNamespace(generate_content=self._gen)
        self.calls = []

    def _gen(self, model, contents, config=None):
        prompt = contents[-1]
        self.calls.append(prompt[:40])
        if "Name the shared audience need" in prompt:
            kw = prompt.split("Keyword hint:")[1].split("\n")[0].strip()
            out = {"label": f"Gemini: {kw}", "audience_need": f"People need help with {kw}", "search_query": kw, "confidence": 0.9}
        elif "Recommend ONE piece" in prompt:
            topic = prompt.split("TOPIC:")[1].split("\n")[0].strip()
            out = {"recommended_topic": topic, "content_format": "YouTube long-form", "title": f"{topic} explained", "target_audience": "beginners",
                   "content_angle": "step by step", "suggested_sections": ["intro", "demo"], "cta": "subscribe", "expected_value": "high",
                   "reason": "audience asked", "evidence_ids": self.evidence_ids, "confidence": 0.8}
        elif "Write a content brief" in prompt:
            out = {"title": "Brief title", "hook": "A hook", "target_audience": "students", "format": "YouTube", "length": "10 min",
                   "outline": ["a", "b"], "script": "script text", "cta": "like", "evidence_ids": [1, 99]}
        elif "frames from a video" in prompt:
            out = {"visual_topics": ["terminal showing docker compose"], "visible_text": "", "context": "tutorial", "confidence": 0.8}
        elif "screenshot" in prompt:
            out = {"visible_text": "Error: model failed to deploy", "topic": self.image_topic, "intent": "complaint",
                   "pain_point": "deployment failure", "sentiment": "negative", "entities": ["model"], "context": "terminal", "confidence": 0.9}
        else:
            out = {"topic": "deployment", "intent": "confusion", "pain_point": "can't deploy", "sentiment": "negative", "confidence": 0.8}
        return SimpleNamespace(text=json.dumps(out))


class FakeWhisper:
    def __init__(self, text="I don't know how to deploy my model. I tried three tutorials."):
        self.text = text

    def transcribe(self, path, fp16=False):
        return {"text": self.text, "language": "en"}
