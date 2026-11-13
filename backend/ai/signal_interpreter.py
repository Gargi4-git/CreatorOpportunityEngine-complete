import sys
import pandas as pd

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


CLUSTER_FILE = "data/processed/clustered_comments.csv"
TREND_FILE = "data/processed/trend_signals.csv"

OUTPUT_FILE = (
    "data/processed/interpreted_signals.csv"
)


NEED_KEYWORDS = {

    "Practical AI/ML projects": [
        "project",
        "projects",
        "build",
        "building"
    ],

    "AI/ML career and internship guidance": [
        "internship",
        "job",
        "career",
        "resume",
        "placement"
    ],

    "Finding useful datasets": [
        "dataset",
        "datasets",
        "data"
    ],

    "AI/ML learning roadmap": [
        "roadmap",
        "learn",
        "learning",
        "beginner",
        "course"
    ],

    "AI model deployment": [
        "deploy",
        "deployment",
        "production",
        "flask",
        "fastapi"
    ],

    "Choosing AI tools": [
        "tool",
        "tools",
        "library",
        "framework"
    ]
}


def detect_needs(texts):

    combined_text = " ".join(
        texts
    ).lower()

    needs = []

    for need, keywords in NEED_KEYWORDS.items():

        if any(
            keyword in combined_text
            for keyword in keywords
        ):

            needs.append(need)

    if not needs:
        needs.append(
            "General topic guidance"
        )

    return needs


def build_problem(
    topic,
    needs,
    pain_ratio
):

    needs_text = ", ".join(
        needs
    )

    if pain_ratio >= 0.60:

        return (
            f"The audience is actively struggling "
            f"with {topic.lower()} and wants "
            f"practical guidance around "
            f"{needs_text.lower()}."
        )

    if pain_ratio >= 0.35:

        return (
            f"The audience has recurring questions "
            f"about {topic.lower()}, especially "
            f"around {needs_text.lower()}."
        )

    return (
        f"The audience shows interest in "
        f"{topic.lower()}, particularly "
        f"{needs_text.lower()}."
    )


def analyze_signals():

    print("\n====================================")
    print("AUDIENCE SIGNAL INTERPRETATION")
    print("====================================")

    clustered_df = pd.read_csv(
        CLUSTER_FILE
    )

    trend_df = pd.read_csv(
        TREND_FILE
    )

    clustered_df = clustered_df[
        clustered_df["cluster_id"] != -1
    ]

    results = []

    for _, signal in trend_df.iterrows():

        cluster_id = int(
            signal["cluster_id"]
        )

        cluster_comments = clustered_df[
            clustered_df["cluster_id"]
            == cluster_id
        ]

        if cluster_comments.empty:
            continue

        needs = detect_needs(
            cluster_comments["text"]
            .tolist()
        )

        topic = (
            cluster_comments["topic"]
            .mode()
            .iloc[0]
        )

        pain_ratio = float(
            cluster_comments["sentiment"]
            .eq("negative")
            .mean()
        )

        audience_problem = build_problem(
            topic,
            needs,
            pain_ratio
        )

        content_recommendation = (
            "Create practical, "
            f"action-oriented content about "
            f"{topic.lower()} covering "
            f"{', '.join(needs).lower()}."
        )

        results.append({

            "cluster_id":
                cluster_id,

            "comment_count":
                len(cluster_comments),

            "total_engagement":
                int(
                    cluster_comments[
                        "engagement"
                    ]
                    .fillna(0)
                    .sum()
                ),

            "average_engagement":
                round(
                    cluster_comments[
                        "engagement"
                    ]
                    .fillna(0)
                    .mean(),
                    2
                ),

            "dominant_topic":
                topic,

            "pain_ratio":
                round(
                    pain_ratio,
                    3
                ),

            "platforms":
                str(signal.get("platforms") if "platforms" in signal and pd.notna(signal.get("platforms")) else signal.get("platforms_x", "")),

            "recent_comments":
                int(
                    signal["recent_comments"]
                ),

            "previous_comments":
                int(
                    signal["previous_comments"]
                ),

            "growth_percent":
                float(
                    signal["growth_percent"]
                ),

            "trend_score":
                float(
                    signal["trend_score"]
                ),

            "demand_score":
                float(
                    signal["demand_score"]
                ),

            "engagement_score":
                float(
                    signal["engagement_score"]
                ),

            "pain_score":
                float(
                    signal["pain_score"]
                ),

            "actionability_score":
                float(
                    signal["actionability_score"]
                ),

            "cross_platform_score":
                float(
                    signal["cross_platform_score"]
                ),

            "final_opportunity_score":
                float(
                    signal[
                        "final_opportunity_score"
                    ]
                ),

            "audience_needs":
                " | ".join(needs),

            "audience_problem":
                audience_problem,

            "content_recommendation":
                content_recommendation
        })

    result_df = pd.DataFrame(
        results
    )

    result_df = result_df.sort_values(
        "final_opportunity_score",
        ascending=False
    )

    result_df[
        "opportunity_rank"
    ] = range(
        1,
        len(result_df) + 1
    )

    result_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(
        f"\nAudience signals: "
        f"{len(result_df)}"
    )

    print(
        "\nTop signals:"
    )

    print(
        result_df[
            [
                "opportunity_rank",
                "dominant_topic",
                "audience_needs",
                "final_opportunity_score"
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
    analyze_signals()