from typing import Tuple


# Keywords associated with each topic
TOPIC_KEYWORDS = {
    "Python Projects": [
        "python",
        "projects",
        "resume",
    ],

    "Machine Learning": [
        "machine learning",
        "ml",
        "machine learning projects",
        "datasets",
    ],

    "GenAI": [
        "genai",
        "generative ai",
        "ai tools",
        "ai project",
    ],

    "AI Career": [
        "internship",
        "career",
        "job",
        "resume",
    ],

    "Learning Roadmap": [
        "roadmap",
        "beginner",
        "learn",
        "learning",
    ],

    "Deployment": [
        "deploy",
        "deployment",
        "production",
    ],

    "Web Development": [
        "fastapi",
        "flask",
        "web application",
    ],
}


def detect_topic(text: str) -> Tuple[str, float]:
    """
    Detect the most relevant topic from a comment.

    Returns:
        topic: detected topic
        confidence: simple keyword-based confidence score
    """

    text = text.lower()

    topic_scores = {}

    for topic, keywords in TOPIC_KEYWORDS.items():

        score = 0

        for keyword in keywords:

            if keyword in text:
                score += 1

        if score > 0:
            topic_scores[topic] = score

    # No topic found
    if not topic_scores:
        return "Other", 0.0

    # Select topic with highest score
    best_topic = max(
        topic_scores,
        key=topic_scores.get
    )

    # Simple confidence calculation
    matched_keywords = topic_scores[best_topic]
    total_keywords = len(TOPIC_KEYWORDS[best_topic])

    confidence = matched_keywords / total_keywords

    return best_topic, round(confidence, 2)


if __name__ == "__main__":

    test_comments = [
        "I struggle to find good Python projects for my resume.",
        "I want practical machine learning projects with real datasets.",
        "Please make a roadmap for learning GenAI as a beginner.",
        "How do I deploy my AI model into production?",
        "Can you compare FastAPI and Flask?",
        "I don't know which AI tools I should learn for getting an internship.",
        "This comment is about something completely different.",
    ]

    for comment in test_comments:

        topic, confidence = detect_topic(comment)

        print(f"\nComment: {comment}")
        print(f"Topic: {topic}")
        print(f"Confidence: {confidence}")