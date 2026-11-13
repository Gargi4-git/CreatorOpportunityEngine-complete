import pandas as pd

from backend.ai.gemini import generate_opportunity


SIGNALS_FILE = "data/processed/interpreted_signals.csv"
RECOMMENDATIONS_FILE = "data/processed/gemini_recommendations.csv"


def load_best_opportunity():
    signals_df = pd.read_csv(SIGNALS_FILE)

    if signals_df.empty:
        raise ValueError("No audience signals are available.")

    score_col = "final_opportunity_score" if "final_opportunity_score" in signals_df.columns else "opportunity_score"

    signals_df = signals_df.sort_values(
        by=score_col,
        ascending=False
    )

    best = signals_df.iloc[0]

    return {
        "cluster_id": int(best["cluster_id"]),
        "opportunity_score": float(best[score_col]),
        "comment_count": int(best["comment_count"]),
        "total_engagement": int(best["total_engagement"]),
        "average_engagement": float(best["average_engagement"]),
        "audience_needs": str(best.get("audience_needs", "")),
        "audience_problem": str(best.get("audience_problem", "")),
        "pain_ratio": float(best.get("pain_ratio", 0.0)),
        "content_recommendation": str(
            best.get("content_recommendation", "")
        ),
    }


def build_context(opportunity):
    return f"""
AUDIENCE INTELLIGENCE

Opportunity Score:
{opportunity['opportunity_score']}

Audience Comments:
{opportunity['comment_count']}

Total Engagement:
{opportunity['total_engagement']}

Average Engagement:
{opportunity['average_engagement']}

Audience Needs:
{opportunity['audience_needs']}

Audience Problem:
{opportunity['audience_problem']}

Pain Ratio:
{opportunity['pain_ratio']}

Existing Recommendation:
{opportunity['content_recommendation']}
"""


def generate_next_video():
    opportunity = load_best_opportunity()
    context = build_context(opportunity)

    prompt = f"""
You are the Creator Opportunity Engine AI Creator Strategist.

Use ONLY the audience intelligence provided below.

{context}

Determine the best next video for the creator.

Return exactly:

VIDEO IDEA:
A clear video concept.

TARGET AUDIENCE:
Who should watch it?

AUDIENCE PROBLEM:
What problem are they facing?

WHY NOW:
Why is this opportunity worth addressing now?

VIDEO FORMAT:
Recommended format.

TITLE:
One strong YouTube title.

HOOK:
A strong opening hook.

CONTENT:
A short explanation of what the video should teach.

Do not invent audience statistics.
"""

    return generate_opportunity(prompt)


def generate_video_ideas(count=10):
    opportunity = load_best_opportunity()
    context = build_context(opportunity)

    prompt = f"""
You are an AI content strategist.

Generate {count} YouTube video ideas based on this
real audience intelligence:

{context}

The ideas must directly address the audience's problems
and needs.

For every idea provide:

IDEA:
TITLE:
TARGET AUDIENCE:
PROBLEM SOLVED:
FORMAT:

Do not invent audience statistics.
Avoid generic ideas.
"""

    return generate_opportunity(prompt)


def generate_title_ideas():
    opportunity = load_best_opportunity()
    context = build_context(opportunity)

    prompt = f"""
You are a YouTube title strategist.

Based on this audience intelligence:

{context}

Generate 10 strong YouTube titles.

Requirements:
- Clear
- Specific
- Relevant to the audience problem
- Clickable without being misleading
- Suitable for educational creators

Return a numbered list.
"""

    return generate_opportunity(prompt)


def generate_video_outline():
    opportunity = load_best_opportunity()
    context = build_context(opportunity)

    prompt = f"""
Create a detailed YouTube video outline based on:

{context}

Return:

VIDEO TITLE:
TARGET AUDIENCE:

1. HOOK
2. INTRODUCTION
3. AUDIENCE PROBLEM
4. CORE CONCEPT
5. STEP-BY-STEP CONTENT
6. PRACTICAL EXAMPLE
7. COMMON MISTAKES
8. SUMMARY
9. CALL TO ACTION

Keep the outline practical and creator-focused.
"""

    return generate_opportunity(prompt)


def generate_video_script():
    opportunity = load_best_opportunity()
    context = build_context(opportunity)

    prompt = f"""
You are an expert educational YouTube scriptwriter.

Create a complete video script based on:

{context}

Structure:

TITLE

HOOK

INTRODUCTION

SECTION 1

SECTION 2

SECTION 3

PRACTICAL EXAMPLE

COMMON MISTAKES

CONCLUSION

CALL TO ACTION

Write naturally as a creator speaking to viewers.

Do not invent audience statistics.
Keep the script educational and practical.
"""

    return generate_opportunity(prompt)


def generate_content_calendar(days=7):
    opportunity = load_best_opportunity()
    context = build_context(opportunity)

    prompt = f"""
Create a {days}-day content plan for a creator.

Use this audience intelligence:

{context}

Create a practical publishing schedule.

For each day provide:

DAY:
CONTENT TYPE:
VIDEO IDEA:
TITLE:
PURPOSE:

Use the main audience opportunity as the central theme,
but create supporting content around it.
"""

    return generate_opportunity(prompt)


def creator_chat(question):
    opportunity = load_best_opportunity()
    context = build_context(opportunity)

    prompt = f"""
You are the Creator Opportunity Engine AI assistant.

You help creators understand audience demand and
turn audience signals into content decisions.

Current audience intelligence:

{context}

Creator question:

{question}

Answer clearly and practically.

Use the provided audience intelligence when relevant.
Do not invent statistics.
If the question is unrelated to creator strategy,
say that it is outside the current system scope.
"""

    return generate_opportunity(prompt)
