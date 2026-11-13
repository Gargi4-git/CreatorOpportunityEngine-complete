import os
import sys
import pandas as pd

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


YOUTUBE_FILE = "data/raw/youtube_comments.csv"
REDDIT_FILE = "data/raw/reddit_comments.csv"

OUTPUT_FILE = "data/raw/combined_comments.csv"


REQUIRED_COLUMNS = [
    "id",
    "source",
    "author",
    "text",
    "timestamp",
    "engagement",
    "url"
]


def load_source_file(file_path):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return pd.DataFrame(columns=REQUIRED_COLUMNS)

    df = pd.read_csv(file_path)

    for column in REQUIRED_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    df = df[REQUIRED_COLUMNS]

    return df


def combine_datasets():

    print("\n====================================")
    print("COMBINING AUDIENCE DATA")
    print("====================================")

    youtube_df = load_source_file(
        YOUTUBE_FILE
    )

    reddit_df = load_source_file(
        REDDIT_FILE
    )

    print(
        f"\nYouTube comments: {len(youtube_df)}"
    )

    print(
        f"Reddit comments: {len(reddit_df)}"
    )

    combined_df = pd.concat(
        [
            youtube_df,
            reddit_df
        ],
        ignore_index=True
    )

    # Remove empty comments
    combined_df = combined_df[
        combined_df["text"].notna()
    ]

    combined_df["text"] = (
        combined_df["text"]
        .astype(str)
        .str.strip()
    )

    combined_df = combined_df[
        combined_df["text"] != ""
    ]

    # Remove duplicate comments
    combined_df = combined_df.drop_duplicates(
        subset=["text"]
    )

    # Reset index
    combined_df = combined_df.reset_index(
        drop=True
    )

    # Make sure engagement is numeric
    combined_df["engagement"] = pd.to_numeric(
        combined_df["engagement"],
        errors="coerce"
    ).fillna(0)

    # Save
    combined_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(
        "\n------------------------------------"
    )

    print(
        f"Total comments: {len(combined_df)}"
    )

    print(
        f"YouTube: "
        f"{len(combined_df[combined_df['source'] == 'youtube'])}"
    )

    print(
        f"Reddit: "
        f"{len(combined_df[combined_df['source'] == 'reddit'])}"
    )

    print(
        "\nSource distribution:"
    )

    print(
        combined_df["source"]
        .value_counts()
    )

    print(
        "\nTotal engagement:"
    )

    print(
        int(combined_df["engagement"].sum())
    )

    print(
        f"\nSaved combined dataset to:"
        f"\n{OUTPUT_FILE}"
    )

    print(
        "\nSample comments:"
    )

    print(
        combined_df[
            [
                "source",
                "author",
                "text",
                "engagement"
            ]
        ]
        .head(10)
        .to_string(index=False)
    )


if __name__ == "__main__":
    combine_datasets()
