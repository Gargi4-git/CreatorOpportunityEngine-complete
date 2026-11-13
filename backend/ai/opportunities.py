import pandas as pd


INPUT_FILE = "data/processed/analyzed_comments.csv"
OUTPUT_FILE = "data/processed/opportunities.csv"


def calculate_opportunity_score(
    demand_score: float,
    pain_score: float,
    engagement_score: float,
    competition_score: float,
) -> float:
    """
    Calculate the opportunity score.

    Higher score = better content opportunity.

    All input values should be between 0 and 1.
    """

    score = (
        0.35 * demand_score
        + 0.30 * pain_score
        + 0.20 * engagement_score
        + 0.15 * (1 - competition_score)
    )

    return round(score * 100, 2)


def generate_opportunity(
    topic: str,
    sentiment: str,
    engagement: int,
) -> dict:

    # Demand
    demand_score = 0.5

    if sentiment == "negative":
        demand_score += 0.2

    # Pain
    pain_score = 0.3

    if sentiment == "negative":
        pain_score = 0.9

    # Engagement
    engagement_score = min(engagement / 100, 1.0)

    # Placeholder for now
    competition_score = 0.5

    # Calculate final score
    opportunity_score = calculate_opportunity_score(
        demand_score=demand_score,
        pain_score=pain_score,
        engagement_score=engagement_score,
        competition_score=competition_score,
    )

    content_idea = (
        f"Create practical content about {topic} "
        f"that directly solves audience problems."
    )

    return {
        "topic": topic,
        "opportunity_score": opportunity_score,
        "content_idea": content_idea,
    }


def analyze_opportunities():

    # Load analyzed comments
    df = pd.read_csv(INPUT_FILE)

    opportunities = []

    # Analyze every comment
    for _, row in df.iterrows():

        result = generate_opportunity(
            topic=row["topic"],
            sentiment=row["sentiment"],
            engagement=int(row["engagement"]),
        )

        opportunities.append({
            "comment_id": row["id"],
            "source": row["source"],
            "topic": result["topic"],
            "sentiment": row["sentiment"],
            "engagement": row["engagement"],
            "opportunity_score": result["opportunity_score"],
            "content_idea": result["content_idea"],
        })

    # Convert results to DataFrame
    opportunities_df = pd.DataFrame(opportunities)

    # Sort highest opportunity first
    opportunities_df = opportunities_df.sort_values(
        by="opportunity_score",
        ascending=False,
    )

    # Save results
    opportunities_df.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print("\nOpportunity Analysis Complete!")
    print("--------------------------------")

    print(
        f"Total opportunities: {len(opportunities_df)}"
    )

    print("\nRanked Opportunities:")

    print(
        opportunities_df[
            [
                "comment_id",
                "topic",
                "sentiment",
                "engagement",
                "opportunity_score",
                "content_idea",
            ]
        ].to_string(index=False)
    )

    print(
        f"\nSaved opportunities to: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    analyze_opportunities()