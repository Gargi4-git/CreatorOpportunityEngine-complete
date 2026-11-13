import sys
import pandas as pd

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from sentence_transformers import SentenceTransformer
from sklearn.cluster import DBSCAN, KMeans


INPUT_FILE = "data/processed/analyzed_comments.csv"
OUTPUT_FILE = "data/processed/clustered_comments.csv"


def cluster_comments():

    print("\n====================================")
    print("AUDIENCE COMMENT CLUSTERING")
    print("====================================")

    df = pd.read_csv(INPUT_FILE)

    print(
        f"\nComments loaded: {len(df)}"
    )

    # --------------------------------
    # Load embedding model
    # --------------------------------

    print(
        "\nLoading embedding model..."
    )

    model = SentenceTransformer(
        "all-MiniLM-L6-v2"
    )

    print(
        "Embedding model loaded."
    )

    # --------------------------------
    # Create embeddings
    # --------------------------------

    print(
        "\nCreating semantic embeddings..."
    )

    embeddings = model.encode(
        df["clean_text"].tolist(),
        show_progress_bar=True,
        normalize_embeddings=True
    )

    print(
        "Embeddings created."
    )

    # --------------------------------
    # DBSCAN clustering
    # --------------------------------

    print(
        "\nRunning semantic clustering..."
    )

    clustering_model = DBSCAN(
        eps=0.38,
        min_samples=3,
        metric="cosine"
    )

    cluster_labels = clustering_model.fit_predict(
        embeddings
    )

    if len(set(cluster_labels) - {-1}) == 0:
        clustering_model = DBSCAN(
            eps=0.48,
            min_samples=2,
            metric="cosine"
        )
        cluster_labels = clustering_model.fit_predict(
            embeddings
        )

    if len(set(cluster_labels) - {-1}) == 0:
        print(
            "\nAdaptive clustering: grouping conversational patterns..."
        )
        k = min(5, max(2, len(df) // 5))
        kmeans = KMeans(n_clusters=k, random_state=42, n_init="auto")
        cluster_labels = kmeans.fit_predict(embeddings)

    df["cluster_id"] = cluster_labels

    # --------------------------------
    # Save
    # --------------------------------

    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # --------------------------------
    # Statistics
    # --------------------------------

    unique_clusters = set(
        cluster_labels
    )

    number_of_clusters = len(
        unique_clusters
        - {-1}
    )

    noise_count = sum(
        label == -1
        for label in cluster_labels
    )

    print(
        "\n===================================="
    )

    print(
        "Clustering Complete!"
    )

    print(
        "===================================="
    )

    print(
        f"Total comments: {len(df)}"
    )

    print(
        f"Clusters found: {number_of_clusters}"
    )

    print(
        f"Noise comments: {noise_count}"
    )

    print(
        "\nCluster distribution:"
    )

    print(
        df["cluster_id"]
        .value_counts()
        .sort_index()
    )

    # --------------------------------
    # Show cluster examples
    # --------------------------------

    print(
        "\nCluster examples:"
    )

    for cluster_id in sorted(
        df["cluster_id"].unique()
    ):

        if cluster_id == -1:
            continue

        cluster_df = df[
            df["cluster_id"] == cluster_id
        ]

        print(
            f"\nCluster {cluster_id}"
        )

        print(
            f"Comments: "
            f"{len(cluster_df)}"
        )

        for text in cluster_df[
            "text"
        ].head(3):

            print(
                f"- {str(text)[:150]}"
            )

    print(
        f"\nSaved clustered data to:"
        f"\n{OUTPUT_FILE}"
    )


if __name__ == "__main__":
    cluster_comments()