from __future__ import annotations
from typing import Annotated, TypedDict, Optional, List
import operator

from models.serp import SerpData
from models.outline import SerpAnalysis, ArticleOutline
from models.article import ArticleOutput, ValidationResult


class ArticleState(TypedDict):
    # ── Inputs ──────────────────────────────────────────────
    topic: str
    target_word_count: int
    language: str
    use_mock: bool

    # ── Node outputs ─────────────────────────────────────────
    serp_data: Optional[SerpData]
    serp_analysis: Optional[SerpAnalysis]   # also carries parsed_keyword
    outline: Optional[ArticleOutline]

    # Annotated with operator.add so LangGraph appends rather than overwrites
    generated_sections: Annotated[List[str], operator.add]

    article_output: Optional[ArticleOutput]
    validation_result: Optional[ValidationResult]

    # ── Control ──────────────────────────────────────────────
    # NOTE: thread_id is NOT stored here — it lives in
    # config["configurable"]["thread_id"] and is owned by LangGraph.
    error: Optional[str]
