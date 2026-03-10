"""Node 5: Assemble final ArticleOutput — body, keyword analysis, FAQ."""
from __future__ import annotations
import os
import re
from typing import List
from pydantic import BaseModel
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage

from graph.state import ArticleState
from models.article import (
    ArticleOutput, KeywordAnalysis, KeywordOccurrence, FAQItem,
)
from models.outline import InternalLinkSuggestion, ExternalReference


# ── FAQ structured schema ──────────────────────────────────────────────────────

class FAQList(BaseModel):
    items: List[FAQItem]


# ── Keyword analysis ───────────────────────────────────────────────────────────

def _compute_keyword_analysis(
    body: str,
    primary_keyword: str,
    secondary_keywords: List[str],
    sections: List[str],
) -> KeywordAnalysis:
    body_lower = body.lower()
    words = body_lower.split()
    total = len(words) or 1

    pk_count = body_lower.count(primary_keyword.lower())

    sk_occurrences: List[KeywordOccurrence] = []
    for kw in secondary_keywords:
        count = body_lower.count(kw.lower())
        present_in: List[str] = []
        for sec in sections:
            if kw.lower() in sec.lower():
                # Extract heading from section
                first_line = sec.split("\n")[0].lstrip("#").strip()
                if first_line and first_line not in present_in:
                    present_in.append(first_line)
        sk_occurrences.append(KeywordOccurrence(
            keyword=kw,
            count=count,
            sections_present=present_in,
        ))

    return KeywordAnalysis(
        primary_keyword=primary_keyword,
        primary_keyword_count=pk_count,
        secondary_keywords=sk_occurrences,
        keyword_density=round(pk_count / total, 4),
    )


# ── FAQ generation ─────────────────────────────────────────────────────────────

def _generate_faq(questions: List[str], primary_keyword: str) -> List[FAQItem]:
    if not questions:
        return []

    llm = ChatAnthropic(
        model="claude-sonnet-4-6",
        temperature=0.3,
    ).with_structured_output(FAQList)

    system = (
        "You are a content writer. For each question provided, write a concise, accurate answer "
        "of 2-4 sentences. Naturally include the topic keyword where appropriate. "
        "Do not repeat the question in the answer."
    )
    user = f"Topic keyword: {primary_keyword}\n\nQuestions:\n" + "\n".join(
        f"- {q}" for q in questions
    )

    result: FAQList = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    return result.items


# ── Fallback questions ─────────────────────────────────────────────────────────

def _fallback_questions(subtopics: List[str], primary_keyword: str) -> List[str]:
    """Generate generic FAQ questions from subtopics when PAA is unavailable."""
    questions = [f"What is the best approach to {primary_keyword}?"]
    for topic in subtopics[:3]:
        questions.append(f"How does {topic} relate to {primary_keyword}?")
    return questions


# ── Main node ─────────────────────────────────────────────────────────────────

def postprocess_node(state: ArticleState) -> dict:
    outline = state["outline"]
    analysis = state["serp_analysis"]
    serp_data = state.get("serp_data")
    generated_sections = state.get("generated_sections", [])

    if not outline or not analysis:
        return {"error": "Missing outline or analysis for postprocessing"}

    # 1. Assemble body markdown
    body_markdown = f"# {outline.h1_title}\n\n" + "\n\n".join(generated_sections)
    word_count = len(body_markdown.split())

    # 2. Keyword analysis — use serp_analysis.primary_keyword (NOT outline.h1_title)
    primary_keyword = analysis.primary_keyword
    keyword_analysis = _compute_keyword_analysis(
        body=body_markdown,
        primary_keyword=primary_keyword,
        secondary_keywords=analysis.secondary_keywords,
        sections=generated_sections,
    )

    # 3. FAQ — use PAA questions or fallback to subtopic-derived questions
    paa_questions = [p.question for p in serp_data.people_also_ask] if serp_data else []
    if not paa_questions:
        paa_questions = _fallback_questions(analysis.common_subtopics, primary_keyword)

    faq = _generate_faq(paa_questions, primary_keyword)

    # 4. Assemble ArticleOutput
    # Enforce meta title character bounds (50-60)
    meta_title = outline.meta_title[:60]
    if len(meta_title) < 50:
        # Append year as a safe, natural qualifier to reach minimum length
        from datetime import date
        year = str(date.today().year)
        if year not in meta_title:
            meta_title = f"{meta_title} {year}"
        meta_title = meta_title[:60]

    # Enforce meta description character bounds (150-160)
    meta_description = outline.meta_description[:160]

    article_output = ArticleOutput(
        thread_id="",  # will be set in main.py after retrieval
        h1=outline.h1_title,
        meta_title=meta_title,
        meta_description=meta_description,
        body_markdown=body_markdown,
        word_count=word_count,
        keyword_analysis=keyword_analysis,
        internal_links=outline.internal_links,
        external_references=outline.external_references,
        faq=faq,
        validation_results=None,
    )

    return {"article_output": article_output}
