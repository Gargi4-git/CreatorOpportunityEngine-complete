import pandas as pd
import re


def clean_text(text: str) -> str:
    """Clean a single comment."""

    if not isinstance(text, str):
        return ""

    # Convert to lowercase
    text = text.lower()

    # Remove URLs
    text = re.sub(r"https?://\S+|www\.\S+", "", text)

    # Remove extra spaces
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def load_and_clean_data(file_path: str) -> pd.DataFrame:
    """Load audience data and clean the text."""

    df = pd.read_csv(file_path)

    # Remove rows without text
    df = df.dropna(subset=["text"])

    # Clean comments
    df["clean_text"] = df["text"].apply(clean_text)

    # Remove empty comments
    df = df[df["clean_text"] != ""]

    # Remove duplicate comments
    df = df.drop_duplicates(subset=["clean_text"])

    return df


if __name__ == "__main__":
    file_path = "data/sample/audience_comments.csv"

    df = load_and_clean_data(file_path)

    print("\nCleaned Audience Data:")
    print(df[["id", "source", "text", "clean_text"]].to_string(index=False))

    print(f"\nTotal comments: {len(df)}")