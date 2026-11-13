import sys
import pandas as pd

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from backend.data.cleaner import load_and_clean_data
from backend.data.ingestion import load_all_data
from backend.ai.sentiment import analyze_sentiment
from backend.ai.topics import detect_topic


INPUT_FILE = "data/processed/audience_data.csv"
OUTPUT_FILE = "data/processed/analyzed_comments.csv"


def analyze_comments():

    print("\n====================================")
    print("AUDIENCE COMMENT ANALYSIS")
    print("====================================")

    df = load_and_clean_data(
        INPUT_FILE
    )

    print(
        f"\nComments after cleaning: {len(df)}"
    )

    # -----------------------------
    # Sentiment Analysis
    # -----------------------------

    print(
        "\nRunning sentiment analysis..."
    )

    sentiment_results = df[
        "clean_text"
    ].apply(analyze_sentiment)

    df["sentiment"] = sentiment_results.apply(
        lambda result: result[0]
    )

    df["sentiment_score"] = sentiment_results.apply(
        lambda result: result[1]
    )

    # -----------------------------
    # Topic Detection
    # -----------------------------

    print(
        "Running topic detection..."
    )

    topic_results = df[
        "clean_text"
    ].apply(detect_topic)

    df["topic"] = topic_results.apply(
        lambda result: result[0]
    )

    df["topic_confidence"] = topic_results.apply(
        lambda result: result[1]
    )

    # -----------------------------
    # Save
    # -----------------------------

    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(
        "\nAnalysis Complete!"
    )

    print(
        "--------------------------------"
    )

    print(
        f"Total comments analyzed: {len(df)}"
    )

    print(
        "\nSource Distribution:"
    )

    print(
        df["source"].value_counts()
    )

    print(
        "\nSentiment Distribution:"
    )

    print(
        df["sentiment"].value_counts()
    )

    print(
        "\nTop Topics:"
    )

    print(
        df["topic"].value_counts().head(10)
    )

    print(
        f"\nSaved analyzed data to:"
        f"\n{OUTPUT_FILE}"
    )


if __name__ == "__main__":
    analyze_comments()