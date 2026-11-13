from backend.data.ingestion import load_all_data
from backend.ai.analyzer import analyze_comments
from backend.ai.clustering import cluster_comments
from backend.ai.cluster_analyzer import analyze_clusters
from backend.ai.trend_analysis import calculate_trend
from backend.ai.signal_interpreter import analyze_signals
from backend.ai.recommendations import generate_recommendations


def run_pipeline():

    print("\n====================================")
    print("CREATOR OPPORTUNITY ENGINE")
    print("====================================")

    print("\n[1/7] Collecting and unifying audience data...")

    audience_data = load_all_data()

    print(
        f"Unified audience comments: "
        f"{len(audience_data)}"
    )

    print(
        "\n[2/7] Running sentiment and topic analysis..."
    )

    analyze_comments()

    print(
        "\n[3/7] Running semantic clustering..."
    )

    cluster_comments()

    print(
        "\n[4/7] Calculating audience signals..."
    )

    analyze_clusters()

    print(
        "\n[5/7] Detecting trends and cross-platform demand..."
    )

    calculate_trend()

    print(
        "\n[6/7] Interpreting audience problems..."
    )

    analyze_signals()

    print(
        "\n[7/7] Generating Gemini opportunities..."
    )

    generate_recommendations()

    print(
        "\n===================================="
    )

    print(
        "PIPELINE COMPLETE"
    )

    print(
        "===================================="
    )


if __name__ == "__main__":
    run_pipeline()
