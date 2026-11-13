import sys
import pandas as pd

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


INPUT_FILE = "data/processed/clustered_comments.csv"
OUTPUT_FILE = "data/processed/audience_signals.csv"


ACTION_KEYWORDS = [
    "how",
    "which",
    "what",
    "where",
    "recommend",
    "recommendation",
    "help",
    "learn",
    "find",
    "need",
    "should",
    "best",
    "guide",
    "tutorial",
    "project",
    "roadmap",
    "course",
]


def min_max_score(series):

    minimum = series.min()
    maximum = series.max()

    if maximum == minimum:
        return pd.Series(
            [100.0] * len(series),
            index=series.index
        )

    return (
        (series - minimum)
        / (maximum - minimum)
        * 100
    )


def calculate_actionability(text):

    text = str(text).lower()

    matches = sum(
        1
        for keyword in ACTION_KEYWORDS
        if keyword in text
    )

    return matches > 0


def analyze_clusters():

    print("\n====================================")
    print("ADVANCED AUDIENCE INTELLIGENCE")
    print("====================================")

    df = pd.read_csv(INPUT_FILE)

    # Ignore DBSCAN noise
    df = df[df["cluster_id"] != -1].copy()

    if df.empty:

        print(
            "\nNo valid clusters found."
        )

        empty_df = pd.DataFrame()

        empty_df.to_csv(
            OUTPUT_FILE,
            index=False
        )

        return

    # Actionability for each comment
    df["is_actionable"] = (
        df["text"]
        .apply(calculate_actionability)
    )

    signals = []

    for cluster_id, group in df.groupby(
        "cluster_id"
    ):

        comment_count = len(group)

        total_engagement = (
            group["engagement"]
            .fillna(0)
            .sum()
        )

        average_engagement = (
            group["engagement"]
            .fillna(0)
            .mean()
        )

        pain_ratio = (
            group["sentiment"]
            .eq("negative")
            .mean()
        )

        dominant_topic = (
            group["topic"]
            .mode()
            .iloc[0]
            if not group["topic"].mode().empty
            else "Other"
        )

        dominant_sentiment = (
            group["sentiment"]
            .mode()
            .iloc[0]
            if not group["sentiment"].mode().empty
            else "neutral"
        )

        platforms = sorted(
            group["source"]
            .dropna()
            .unique()
            .tolist()
        )

        platform_count = len(platforms)

        cross_platform_score = (
            min(
                platform_count / 2 * 100,
                100
            )
        )

        actionability_score = (
            group["is_actionable"]
            .mean()
            * 100
        )

        signals.append({

            "cluster_id": int(cluster_id),

            "comment_count":
                int(comment_count),

            "total_engagement":
                int(total_engagement),

            "average_engagement":
                round(
                    float(average_engagement),
                    2
                ),

            "pain_ratio":
                round(
                    float(pain_ratio),
                    3
                ),

            "dominant_topic":
                dominant_topic,

            "dominant_sentiment":
                dominant_sentiment,

            "platform_count":
                platform_count,

            "platforms":
                ", ".join(platforms),

            "cross_platform_score":
                round(
                    cross_platform_score,
                    2
                ),

            "actionability_score":
                round(
                    float(actionability_score),
                    2
                ),
        })

    signals_df = pd.DataFrame(
        signals
    )

    # --------------------------------
    # Normalize demand
    # --------------------------------

    signals_df["demand_score"] = (
        min_max_score(
            signals_df["comment_count"]
        )
    )

    # --------------------------------
    # Normalize engagement
    # --------------------------------

    signals_df["engagement_score"] = (
        min_max_score(
            signals_df["average_engagement"]
        )
    )

    # --------------------------------
    # Pain score
    # --------------------------------

    signals_df["pain_score"] = (
        signals_df["pain_ratio"] * 100
    )

    # --------------------------------
    # Opportunity score
    # --------------------------------

    signals_df["opportunity_score"] = (

        signals_df["demand_score"] * 0.30

        + signals_df["pain_score"] * 0.25

        + signals_df["engagement_score"] * 0.20

        + signals_df["cross_platform_score"] * 0.15

        + signals_df["actionability_score"] * 0.10

    ).round(2)

    # Rank
    signals_df = signals_df.sort_values(
        "opportunity_score",
        ascending=False
    )

    signals_df[
        "opportunity_rank"
    ] = range(
        1,
        len(signals_df) + 1
    )

    signals_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(
        "\nAdvanced analysis complete!"
    )

    print(
        "------------------------------------"
    )

    print(
        f"Audience signals: "
        f"{len(signals_df)}"
    )

    print(
        "\nTop opportunities:"
    )

    print(
        signals_df[
            [
                "opportunity_rank",
                "cluster_id",
                "comment_count",
                "pain_ratio",
                "platforms",
                "opportunity_score"
            ]
        ]
        .head(10)
        .to_string(index=False)
    )

    print(
        f"\nSaved to:"
        f"\n{OUTPUT_FILE}"
    )


if __name__ == "__main__":
    analyze_clusters()