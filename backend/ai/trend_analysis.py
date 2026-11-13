import sys
import pandas as pd

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


INPUT_FILE = "data/processed/clustered_comments.csv"
SIGNALS_FILE = "data/processed/audience_signals.csv"

OUTPUT_FILE = "data/processed/trend_signals.csv"


def calculate_trend():

    print("\n====================================")
    print("TREND & CROSS-PLATFORM ANALYSIS")
    print("====================================")

    df = pd.read_csv(INPUT_FILE)

    try:
        signals = pd.read_csv(
            SIGNALS_FILE
        )
    except Exception:
        signals = pd.DataFrame()

    if signals.empty:
        print("\nNo signals available to analyze.")
        return

    # Ignore noise
    df = df[
        df["cluster_id"] != -1
    ].copy()

    if df.empty:

        print(
            "\nNo clustered comments available."
        )

        return

    # Convert timestamps
    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce",
        utc=True
    )

    df = df.dropna(
        subset=["timestamp"]
    )

    if df.empty:

        print(
            "\nNo valid timestamps available."
        )

        return

    # Use latest timestamp in dataset
    # rather than computer's current date.
    dataset_end = df["timestamp"].max()

    recent_start = (
        dataset_end
        - pd.Timedelta(days=30)
    )

    previous_start = (
        dataset_end
        - pd.Timedelta(days=60)
    )

    recent_df = df[
        df["timestamp"] >= recent_start
    ]

    previous_df = df[
        (df["timestamp"] >= previous_start)
        &
        (df["timestamp"] < recent_start)
    ]

    results = []

    for cluster_id in signals[
        "cluster_id"
    ]:

        cluster_recent = recent_df[
            recent_df["cluster_id"]
            == cluster_id
        ]

        cluster_previous = previous_df[
            previous_df["cluster_id"]
            == cluster_id
        ]

        recent_count = len(
            cluster_recent
        )

        previous_count = len(
            cluster_previous
        )

        # --------------------------------
        # Growth
        # --------------------------------

        if previous_count == 0:

            if recent_count > 0:
                growth_percent = 100.0
            else:
                growth_percent = 0.0

        else:

            growth_percent = (
                (
                    recent_count
                    - previous_count
                )
                / previous_count
                * 100
            )

        # --------------------------------
        # Trend score
        # --------------------------------

        if recent_count == 0:

            trend_score = 20.0

        elif previous_count == 0:

            trend_score = 90.0

        else:

            if growth_percent <= -50:
                trend_score = 20

            elif growth_percent <= 0:
                trend_score = 40

            elif growth_percent <= 25:
                trend_score = 55

            elif growth_percent <= 50:
                trend_score = 70

            elif growth_percent <= 100:
                trend_score = 85

            else:
                trend_score = 100

        # --------------------------------
        # Platform evidence
        # --------------------------------

        platforms = set()

        cluster_all = df[
            df["cluster_id"]
            == cluster_id
        ]

        platforms.update(
            cluster_all["source"]
            .dropna()
            .unique()
        )

        platform_count = len(
            platforms
        )

        if platform_count >= 2:
            cross_platform_signal = 100
        elif platform_count == 1:
            cross_platform_signal = 50
        else:
            cross_platform_signal = 0

        results.append({

            "cluster_id":
                int(cluster_id),

            "recent_comments":
                int(recent_count),

            "previous_comments":
                int(previous_count),

            "growth_percent":
                round(
                    growth_percent,
                    2
                ),

            "trend_score":
                float(trend_score),

            "platform_count":
                int(platform_count),

            "platforms":
                ", ".join(
                    sorted(platforms)
                ),

            "cross_platform_signal":
                float(
                    cross_platform_signal
                )
        })

    trend_df = pd.DataFrame(
        results
    )

    # --------------------------------
    # Final opportunity score
    # --------------------------------

    merged = signals.merge(
        trend_df.drop(columns=["platforms", "platform_count"], errors="ignore"),
        on="cluster_id",
        how="left"
    )

    merged[
        "final_opportunity_score"
    ] = (

        merged["demand_score"] * 0.25

        + merged["pain_score"] * 0.20

        + merged["engagement_score"] * 0.15

        + merged["cross_platform_score"] * 0.10

        + merged["actionability_score"] * 0.10

        + merged["trend_score"] * 0.20

    ).round(2)

    merged = merged.sort_values(
        "final_opportunity_score",
        ascending=False
    )

    merged[
        "opportunity_rank"
    ] = range(
        1,
        len(merged) + 1
    )

    merged.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(
        "\nTrend analysis complete!"
    )

    print(
        "------------------------------------"
    )

    print(
        f"Reference date: "
        f"{dataset_end.date()}"
    )

    print(
        "\nTop trending opportunities:"
    )

    print(
        merged[
            [
                "opportunity_rank",
                "cluster_id",
                "recent_comments",
                "previous_comments",
                "growth_percent",
                "trend_score",
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
    calculate_trend()
