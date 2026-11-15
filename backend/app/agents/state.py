from typing import Any, Dict, List, Optional, TypedDict


class PipelineState(TypedDict, total=False):
    analysis_id: str
    options: dict
    source_ids: List[str]
    raw: List[dict]
    records: List[dict]          # normalised audience records (all modalities)
    report: dict                 # data-quality report
    unified: List[dict]          # unified multimodal representations
    E: Any                       # (n, 384) embeddings
    labels: Any                  # cluster label per record (-1 = unclustered)
    clustering: dict
    embedder_name: str
    topic_meta: Dict[int, dict]  # label, audience_need, search_query, confidence, modality_mix
    cluster_ids: List[int]
    df: Any                      # per-record frame for stats
    ctx: dict
    classification: List[dict]
    demand: Dict[int, dict]
    fresh: Dict[int, Optional[float]]
    trends: Dict[int, dict]
    competition: Dict[int, dict]
    opportunities: List[dict]
    warnings: List[str]
    error: Optional[str]
