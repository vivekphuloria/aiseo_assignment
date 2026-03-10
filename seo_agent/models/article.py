from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field


class SEOCheck(BaseModel):
    check_name: str
    passed: bool
    detail: str


class ValidationResult(BaseModel):
    passed: bool
    checks: List[SEOCheck]
    overall_score: int = Field(..., ge=0, le=100, description="Percentage of checks passed")


class KeywordOccurrence(BaseModel):
    keyword: str
    count: int
    sections_present: List[str]


class KeywordAnalysis(BaseModel):
    primary_keyword: str
    primary_keyword_count: int
    secondary_keywords: List[KeywordOccurrence]
    keyword_density: float = Field(..., description="primary_count / total_words")


class FAQItem(BaseModel):
    question: str
    answer: str


class ArticleOutput(BaseModel):
    thread_id: str
    h1: str
    meta_title: str
    meta_description: str
    body_markdown: str = Field(..., description="Full article with ## and ### headings")
    word_count: int
    keyword_analysis: KeywordAnalysis
    internal_links: List[object]
    external_references: List[object]
    faq: List[FAQItem]
    validation_results: Optional[ValidationResult] = None
