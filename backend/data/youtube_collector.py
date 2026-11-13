import os
import re
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from googleapiclient.discovery import build

load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")
OUTPUT_DIR = Path("data/raw")


def extract_video_id(url):
    """
    Extract YouTube video ID from common YouTube URL formats.
    """
    patterns = [
        r"(?:v=)([A-Za-z0-9_-]{11})",
        r"(?:youtu\.be/)([A-Za-z0-9_-]{11})",
        r"(?:youtube\.com/shorts/)([A-Za-z0-9_-]{11})",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    raise ValueError("Could not extract YouTube video ID.")


def create_youtube_client():
    if not API_KEY or API_KEY == "YOUR_YOUTUBE_API_KEY":
        raise ValueError(
            "YOUTUBE_API_KEY was not found in the .env file."
        )

    return build("youtube", "v3", developerKey=API_KEY)


def collect_comments(video_url, max_comments=1000):
    video_id = extract_video_id(video_url)

    print(f"\nYouTube Video ID: {video_id}")

    use_api = bool(API_KEY and API_KEY != "YOUR_YOUTUBE_API_KEY")
    comments = []

    if use_api:
        try:
            youtube = create_youtube_client()
            next_page_token = None

            print("\nCollecting YouTube comments via YouTube API...")
            print("-------------------------------")

            while len(comments) < max_comments:
                request = youtube.commentThreads().list(
                    part="snippet",
                    videoId=video_id,
                    maxResults=min(100, max_comments - len(comments)),
                    pageToken=next_page_token,
                    textFormat="plainText",
                )
                response = request.execute()

                items = response.get("items", [])
                if not items:
                    break

                for item in items:
                    snippet = item["snippet"]["topLevelComment"]["snippet"]

                    comment = {
                        "id": item["id"],
                        "source": "youtube",
                        "author": snippet.get("authorDisplayName", "unknown"),
                        "text": snippet.get("textDisplay", ""),
                        "timestamp": snippet.get("publishedAt", ""),
                        "engagement": snippet.get("likeCount", 0),
                        "url": (
                            f"https://www.youtube.com/watch?v={video_id}&lc={item['id']}"
                        ),
                    }
                    comments.append(comment)

                    if len(comments) >= max_comments:
                        break

                next_page_token = response.get("nextPageToken")
                if not next_page_token:
                    break

                print(f"Collected {len(comments)} comments...")

        except Exception as e:
            print(f"Note: YouTube API call ({e}).")
            print("Switching to backup comment collector...")
            use_api = False

    if not use_api:
        print("\nCollecting YouTube comments...")
        print("-------------------------------")
        try:
            from itertools import islice
            from youtube_comment_downloader import YoutubeCommentDownloader

            downloader = YoutubeCommentDownloader()
            raw_comments = downloader.get_comments_from_url(f"https://www.youtube.com/watch?v={video_id}")

            for item in islice(raw_comments, max_comments):
                cid = item.get("cid", "")
                author = item.get("author", "unknown")
                text = item.get("text", "")
                time_str = item.get("time", "")
                votes = item.get("votes", "0")
                try:
                    engagement = int(votes) if str(votes).isdigit() else 0
                except Exception:
                    engagement = 0

                comments.append({
                    "id": cid,
                    "source": "youtube",
                    "author": author,
                    "text": text,
                    "timestamp": time_str,
                    "engagement": engagement,
                    "url": f"https://www.youtube.com/watch?v={video_id}&lc={cid}",
                })

                if len(comments) % 100 == 0:
                    print(f"Collected {len(comments)} comments...")
        except Exception as err:
            print(f"Collector error: {err}")

    df = pd.DataFrame(comments)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / "youtube_comments.csv"

    df.to_csv(output_file, index=False)

    print(f"\nTotal comments collected: {len(df)}")
    print(f"Saved to: {output_file}")

    return df


if __name__ == "__main__":
    url = input("\nEnter YouTube video URL: ").strip()
    collect_comments(url, max_comments=1000)
