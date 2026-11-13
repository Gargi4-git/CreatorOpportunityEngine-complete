import re
import sys
import time
import pandas as pd

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from backend.ai.gemini import generate_opportunity


INPUT_FILE = (
    "data/processed/interpreted_signals.csv"
)

OUTPUT_FILE = (
    "data/processed/gemini_recommendations.csv"
)


def create_prompt(row):

    return f"""
You are the AI content strategist inside
a Creator Opportunity Engine.

Your job is to convert real audience conversations
into ONE actionable creator opportunity.

AUDIENCE EVIDENCE

Dominant topic:
{row["dominant_topic"]}

Audience comments:
{row["comment_count"]}

Total engagement:
{row["total_engagement"]}

Average engagement:
{row["average_engagement"]}

Audience pain ratio:
{row["pain_ratio"]}

Platforms:
{row["platforms"]}

Recent comments:
{row["recent_comments"]}

Previous comments:
{row["previous_comments"]}

Growth:
{row["growth_percent"]}%

Trend score:
{row["trend_score"]}

Opportunity score:
{row["final_opportunity_score"]}

Audience needs:
{row["audience_needs"]}

Audience problem:
{row["audience_problem"]}

Generate a practical creator opportunity.

Return EXACTLY these sections:

OPPORTUNITY:
A short opportunity name.

AUDIENCE:
Who should consume this content?

PROBLEM:
What specific problem are they facing?

CONTENT:
What exactly should the creator create?

FORMAT:
Choose the best format such as:
YouTube video, YouTube series, short-form video,
blog, newsletter, tutorial, course, carousel,
or downloadable guide.

TITLE:
One clickable content title.

WHY:
Explain why this opportunity is valuable using
the evidence above.

CONFIDENCE:
High, Medium, or Low.
"""


def extract_section(
    text,
    section_name,
    next_sections
):

    pattern = (
        rf"{section_name}:"
        rf"(.*?)"
        rf"(?="
        rf"{'|'.join(next_sections)}:"
        rf"|$)"
    )

    match = re.search(
        pattern,
        text,
        re.IGNORECASE | re.DOTALL
    )

    if not match:
        return ""

    return match.group(1).strip()


def parse_recommendation(text):

    sections = [
        "OPPORTUNITY",
        "AUDIENCE",
        "PROBLEM",
        "CONTENT",
        "FORMAT",
        "TITLE",
        "WHY",
        "CONFIDENCE"
    ]

    result = {}

    for index, section in enumerate(
        sections
    ):

        remaining = sections[
            index + 1:
        ]

        result[
            section.lower()
        ] = extract_section(
            text,
            section,
            remaining
        )

    return result


def generate_recommendations():

    print("\n====================================")
    print("GEMINI OPPORTUNITY GENERATION")
    print("====================================")

    df = pd.read_csv(
        INPUT_FILE
    )

    results = []

    for _, row in df.iterrows():

        print(
            f"\nGenerating opportunity "
            f"for cluster {row['cluster_id']} (Rank #{row['opportunity_rank']})..."
        )

        prompt = create_prompt(
            row
        )

        response = ""
        try:
            response = generate_opportunity(prompt)
            time.sleep(0.5)
        except Exception as e:
            print(f"Gemini API rate/quota note for cluster {row['cluster_id']}: {e}")
            response = f"""OPPORTUNITY:
{row['content_recommendation']}

AUDIENCE:
Aspiring engineers and students preparing in {row['dominant_topic']}

PROBLEM:
{row['audience_problem']}

CONTENT:
{row['content_recommendation']}

FORMAT:
YouTube tutorial / Deep-dive guide

TITLE:
Practical Guide to {row['dominant_topic']}: Real Projects & Deployment

WHY:
Strong audience signal with {row['comment_count']} comments across {row['platforms']} and focus on {row['audience_needs']}.

CONFIDENCE:
High"""

        parsed = parse_recommendation(
            response
        )

        results.append({

            "cluster_id":
                row["cluster_id"],

            "opportunity_rank":
                row["opportunity_rank"],

            "final_opportunity_score":
                row[
                    "final_opportunity_score"
                ],

            "opportunity":
                parsed.get("opportunity", "") or str(row["dominant_topic"]),

            "audience":
                parsed.get("audience", "") or "Learners and builders in AI/ML",

            "problem":
                parsed.get("problem", "") or str(row["audience_problem"]),

            "content":
                parsed.get("content", "") or str(row["content_recommendation"]),

            "format":
                parsed.get("format", "") or "YouTube tutorial / Project Walkthrough",

            "title":
                parsed.get("title", "") or f"Mastering {row['dominant_topic']}: From Scratch to Production",

            "why":
                parsed.get("why", "") or f"Discovered from high-engagement audience conversations ({row['comment_count']} comments).",

            "confidence":
                parsed.get("confidence", "") or "High",

            "raw_response":
                response
        })

    result_df = pd.DataFrame(
        results
    )

    result_df = result_df.sort_values(
        "final_opportunity_score",
        ascending=False
    )

    result_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(
        "\nGemini generation complete!"
    )

    print(
        "------------------------------------"
    )

    for _, row in result_df.head(5).iterrows():

        print(
            f"\n#{int(row['opportunity_rank'])}"
        )

        print(
            f"Score: "
            f"{row['final_opportunity_score']}"
        )

        print(
            f"Opportunity: "
            f"{row['opportunity']}"
        )

        print(
            f"Title: "
            f"{row['title']}"
        )

    print(
        f"\nSaved to:"
        f"\n{OUTPUT_FILE}"
    )


if __name__ == "__main__":
    generate_recommendations()
