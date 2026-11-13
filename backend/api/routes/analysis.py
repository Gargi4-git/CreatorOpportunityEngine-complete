from fastapi import APIRouter
import pandas as pd


router = APIRouter(
    prefix="/analysis",
    tags=["Analysis"]
)


SIGNALS_FILE = (
    "data/processed/interpreted_signals.csv"
)

RECOMMENDATIONS_FILE = (
    "data/processed/gemini_recommendations.csv"
)


@router.get("/opportunities")
def get_opportunities():

    signals_df = pd.read_csv(
        SIGNALS_FILE
    )

    recommendations_df = pd.read_csv(
        RECOMMENDATIONS_FILE
    )

    df = signals_df.merge(
        recommendations_df,
        on=[
            "cluster_id",
            "opportunity_rank",
            "final_opportunity_score"
        ],
        how="left"
    )

    opportunities = []

    for _, row in df.iterrows():

        opportunities.append({

            "cluster_id":
                int(row["cluster_id"]),

            "rank":
                int(row["opportunity_rank"]),

            "score":
                float(
                    row[
                        "final_opportunity_score"
                    ]
                ),

            "comments":
                int(row["comment_count"]),

            "engagement":
                int(row["total_engagement"]),

            "average_engagement":
                float(
                    row[
                        "average_engagement"
                    ]
                ),

            "topic":
                row["dominant_topic"],

            "pain_ratio":
                float(
                    row["pain_ratio"]
                ),

            "platforms":
                str(row["platforms"]),

            "recent_comments":
                int(row["recent_comments"]),

            "previous_comments":
                int(row["previous_comments"]),

            "growth_percent":
                float(row["growth_percent"]),

            "trend_score":
                float(row["trend_score"]),

            "audience_needs":
                str(row["audience_needs"]),

            "audience_problem":
                str(row["audience_problem"]),

            "content_recommendation":
                str(row["content_recommendation"]),

            "opportunity":
                str(row.get("opportunity", "") or ""),

            "audience":
                str(row.get("audience", "") or ""),

            "problem":
                str(row.get("problem", "") or ""),

            "content":
                str(row.get("content", "") or ""),

            "format":
                str(row.get("format", "") or ""),

            "title":
                str(row.get("title", "") or ""),

            "why":
                str(row.get("why", "") or ""),

            "confidence":
                str(row.get("confidence", "") or ""),

            "raw_response":
                str(row.get("raw_response", "") or "")
        })

    return {

        "total_opportunities":
            len(opportunities),

        "opportunities":
            opportunities
    }


@router.get("/summary")
def get_summary():

    signals_df = pd.read_csv(
        SIGNALS_FILE
    )

    return {

        "total_comments":
            int(
                signals_df[
                    "comment_count"
                ].sum()
            ),

        "total_engagement":
            int(
                signals_df[
                    "total_engagement"
                ].sum()
            ),

        "average_engagement":
            round(
                float(
                    signals_df[
                        "average_engagement"
                    ].mean()
                ),
                2
            ),

        "average_opportunity_score":
            round(
                float(
                    signals_df[
                        "final_opportunity_score"
                    ].mean()
                ),
                2
            ),

        "average_trend_score":
            round(
                float(
                    signals_df[
                        "trend_score"
                    ].mean()
                ),
                2
            ),

        "total_signals":
            len(signals_df)
    }
