"""
Zero-shot intent / sentiment / pain classification using EMBEDDING PROTOTYPES (no LLM call).

Each label is described by a handful of prototype sentences. A comment is assigned to the label whose
prototypes it is most similar to (cosine), with a softmax over labels giving a confidence.
This is an unsupervised-style heuristic: it should be validated against a hand-labelled sample
before being reported as 'accuracy'. Gemini-based refinement is added in the Sentiment/Intent agent (Phase 6/7).
"""
from typing import Dict, List

import numpy as np

TEMPERATURE = 0.05

INTENT_PROTOTYPES: Dict[str, List[str]] = {
    "question": ["How does this work?", "What is the difference between these two?", "Can someone explain this to me?"],
    "tutorial_request": ["Please make a tutorial on this topic.", "Can you make a video about this?", "I would love a full course on this."],
    "confusion": ["I am so confused by this.", "I can't understand this concept at all.", "None of this makes sense to me."],
    "complaint": ["This is frustrating and doesn't work.", "I am struggling and tired of the problems.", "This was a waste of my time."],
    "feature_request": ["Please add support for this feature.", "It would be great if you could add this option."],
    "career_request": ["How do I get a job or internship in this field?", "What should I put on my resume to get hired?"],
    "comparison": ["Which one is better, A or B?", "Can you compare these two tools?"],
    "recommendation": ["I recommend this resource, it is great.", "You should check out this book or course."],
    "appreciation": ["Great video, thank you so much!", "This was really helpful, I love your content."],
}
SENTIMENT_PROTOTYPES: Dict[str, List[str]] = {
    "negative": ["I hate this, it is terrible and frustrating.", "I'm stuck and nothing works.", "This is confusing and too difficult."],
    "positive": ["I love this, it is excellent and very helpful.", "Thank you, this was great!"],
    "neutral": ["Here is some information about the topic.", "I am watching this video today."],
}
PAIN_PROTOTYPES = ["I'm stuck and can't figure this out.", "I struggle with this every time.",
                   "This is too confusing and I'm frustrated.", "I don't know where to start and I keep failing."]
NON_PAIN_PROTOTYPES = ["Great video, thanks for sharing!", "I really enjoyed this.", "Here is some neutral information.",
                       "Nice editing and good music."]
REQUEST_INTENTS = {"request", "learning_request", "question", "tutorial_request", "feature_request", "career_request", "comparison", "confusion"}


class PrototypeClassifier:
    def __init__(self, embedder):
        self.e = embedder
        self.intent = self._embed(INTENT_PROTOTYPES)
        self.sent = self._embed(SENTIMENT_PROTOTYPES)
        self.pain = self.e.encode(PAIN_PROTOTYPES)
        self.non_pain = self.e.encode(NON_PAIN_PROTOTYPES)

    def _embed(self, protos: Dict[str, List[str]]):
        return {k: self.e.encode(v) for k, v in protos.items()}

    @staticmethod
    def _scores(E: np.ndarray, protos: Dict[str, np.ndarray]):
        labels = list(protos)
        sims = np.stack([(E @ protos[l].T).max(axis=1) for l in labels], axis=1)  # (n, labels)
        z = np.exp((sims - sims.max(axis=1, keepdims=True)) / TEMPERATURE)
        probs = z / z.sum(axis=1, keepdims=True)
        return labels, probs

    def classify(self, E: np.ndarray) -> List[dict]:
        il, ip = self._scores(E, self.intent)
        sl, sp = self._scores(E, self.sent)
        p_pain = (E @ self.pain.T).max(axis=1)
        p_non = (E @ self.non_pain.T).max(axis=1)
        pz = np.exp((p_pain - np.maximum(p_pain, p_non)) / TEMPERATURE)
        nz = np.exp((p_non - np.maximum(p_pain, p_non)) / TEMPERATURE)
        pain = pz / (pz + nz)
        return [{
            "intent": il[int(ip[i].argmax())], "intent_confidence": round(float(ip[i].max()), 3),
            "sentiment": sl[int(sp[i].argmax())], "sentiment_confidence": round(float(sp[i].max()), 3),
            "pain_score": round(float(pain[i]), 3),
        } for i in range(len(E))]
