from pathlib import Path

import pandas as pd


RAW_DIR = Path("data/raw")
SAMPLE_DIR = Path("data/sample")
PROCESSED_DIR = Path("data/processed")


STANDARD_COLUMNS = [
    "id",
    "source",
    "author",
    "text",
    "timestamp",
    "engagement",
    "url",
]


def normalize_dataframe(df):
    """
    Convert incoming audience data into the
    standard Creator Opportunity Engine format.
    """

    df = df.copy()

    # Add missing columns
    for column in STANDARD_COLUMNS:

        if column not in df.columns:

            if column == "engagement":
                df[column] = 0

            else:
                df[column] = ""

    # Keep only standard columns
    df = df[STANDARD_COLUMNS]

    # Clean basic values
    df["text"] = (
        df["text"]
        .fillna("")
        .astype(str)
    )

    df["source"] = (
        df["source"]
        .fillna("unknown")
        .astype(str)
    )

    df["author"] = (
        df["author"]
        .fillna("unknown")
        .astype(str)
    )

    df["engagement"] = pd.to_numeric(
        df["engagement"],
        errors="coerce"
    ).fillna(0)

    # Remove empty comments
    df = df[
        df["text"].str.strip() != ""
    ]

    # Remove duplicate comments
    df = df.drop_duplicates(
        subset=["text"]
    )

    return df


def load_sample_data():

    file_path = (
        SAMPLE_DIR
        / "audience_comments.csv"
    )

    if not file_path.exists():
        return pd.DataFrame(
            columns=STANDARD_COLUMNS
        )

    df = pd.read_csv(
        file_path
    )

    return normalize_dataframe(df)


def load_youtube_data():

    file_path = (
        RAW_DIR
        / "youtube_comments.csv"
    )

    if not file_path.exists():
        return pd.DataFrame(
            columns=STANDARD_COLUMNS
        )

    df = pd.read_csv(
        file_path
    )

    return normalize_dataframe(df)


def load_all_data(
    include_sample=True,
    include_youtube=True
):

    datasets = []

    if include_sample:

        sample_df = load_sample_data()

        if not sample_df.empty:
            datasets.append(
                sample_df
            )

    if include_youtube:

        youtube_df = load_youtube_data()

        if not youtube_df.empty:
            datasets.append(
                youtube_df
            )

    if not datasets:

        return pd.DataFrame(
            columns=STANDARD_COLUMNS
        )

    combined = pd.concat(
        datasets,
        ignore_index=True
    )

    combined = normalize_dataframe(
        combined
    )

    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file = (
        PROCESSED_DIR
        / "audience_data.csv"
    )

    combined.to_csv(
        output_file,
        index=False
    )

    return combined


if __name__ == "__main__":

    print("\n================================")
    print("CREATOR DATA INGESTION")
    print("================================")

    df = load_all_data()

    print(
        f"\nTotal audience comments: "
        f"{len(df)}"
    )

    print("\nSources:")

    if not df.empty:
        print(
            df["source"]
            .value_counts()
        )

    print(
        "\nSaved unified data to:"
    )

    print(
        "data/processed/audience_data.csv"
    )
