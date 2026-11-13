from typing import Tuple


# Words that usually indicate positive sentiment
POSITIVE_WORDS = {
    "good",
    "great",
    "useful",
    "helpful",
    "love",
    "best",
    "excellent",
    "practical",
    "interesting",
}


# Words that usually indicate negative sentiment
NEGATIVE_WORDS = {
    "struggle",
    "hard",
    "difficult",
    "worst",
    "problem",
    "confusing",
    "too many",
    "don't know",
    "hardest",
    "theoretical",
    "fail",
}


# Phrases that strongly indicate a user pain point
STRONG_NEGATIVE_PHRASES = {
    "i struggle",
    "i don't know",
    "too many",
    "hardest parts",
    "too theoretical",
}


def analyze_sentiment(text: str) -> Tuple[str, float]:
    """
    Analyze the sentiment of a comment.

    Returns:
        sentiment: positive, negative, or neutral
        score: value between -1 and 1
    """

    # Convert text to lowercase
    text = text.lower()

    # Check strong negative phrases first
    for phrase in STRONG_NEGATIVE_PHRASES:
        if phrase in text:
            return "negative", -1.0

    # Count positive words
    positive_count = sum(
        1 for word in POSITIVE_WORDS
        if word in text
    )

    # Count negative words
    negative_count = sum(
        1 for word in NEGATIVE_WORDS
        if word in text
    )

    # No sentiment detected
    if positive_count == 0 and negative_count == 0:
        return "neutral", 0.0

    # Calculate sentiment score
    total = positive_count + negative_count

    score = (positive_count - negative_count) / total

    # Determine sentiment
    if negative_count > positive_count:
        sentiment = "negative"

    elif positive_count > negative_count:
        sentiment = "positive"

    else:
        sentiment = "neutral"

    return sentiment, round(score, 2)


# Test the sentiment analyzer
if __name__ == "__main__":

    test_comments = [
        "This is a great and useful project.",
        "I struggle to find good projects.",
        "The tutorial is confusing.",
        "Python is interesting.",
        "There are too many technologies to learn.",
        "I don't know which AI tools to learn.",
        "This is a practical project.",
    ]

    for comment in test_comments:

        sentiment, score = analyze_sentiment(comment)

        print(f"\nComment: {comment}")
        print(f"Sentiment: {sentiment}")
        print(f"Score: {score}")