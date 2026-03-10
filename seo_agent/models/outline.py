from typing import List, Literal
from pydantic import BaseModel, Field


class SerpAnalysis(BaseModel):
    primary_keyword: str = Field(..., description="Exact keyword Google is rewarding")
    secondary_keywords: List[str] = Field(..., description="5-8 related keywords from titles/snippets")
    common_subtopics: List[str] = Field(..., description="Subtopics appearing in 3+ results")
    content_format: Literal["listicle", "how-to", "guide", "comparison"] = Field(
        ..., description="Dominant content format"
    )
    search_intent: Literal["informational", "commercial", "navigational"] = Field(
        ..., description="Primary search intent"
    )
    competitor_h2_patterns: List[str] = Field(
        ..., description="Common H2-level topic patterns inferred from titles and snippets"
    )


class InternalLinkSuggestion(BaseModel):
    anchor_text: str = Field(..., description="Anchor text phrase in the article")
    suggested_target_topic: str = Field(..., description="Topic of the page to link to")
    context_hint: str = Field(..., description="Section heading where this link should appear")


class ExternalReference(BaseModel):
    source_name: str
    source_url: str
    placement_section: str = Field(..., description="Section heading where citation fits")
    relevance_note: str


class OutlineSection(BaseModel):
    heading: str = Field(..., description="H2 or H3 heading text")
    heading_level: int = Field(..., ge=2, le=3, description="2 for H2, 3 for H3")
    description: str = Field(..., description="What this section should cover")
    keywords_to_include: List[str] = Field(..., description="Section-specific keywords")
    target_word_count: int = Field(..., ge=50, description="Word budget for this section")


class ArticleOutline(BaseModel):
    h1_title: str = Field(..., description="H1 title containing the primary keyword")
    meta_title: str = Field(..., description="Meta title, 50-60 characters")
    meta_description: str = Field(..., description="Meta description, 150-160 characters")
    sections: List[OutlineSection]
    internal_links: List[InternalLinkSuggestion] = Field(..., min_length=3, max_length=5)
    external_references: List[ExternalReference] = Field(..., min_length=2, max_length=4)
    search_intent: str
