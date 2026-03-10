"""Node 6: Programmatic SEO validation — no LLM call."""
from __future__ import annotations
import re
from typing import List

from graph.state import ArticleState
from models.article import ArticleOutput, SEOCheck, ValidationResult
from models.outline import ArticleOutline


# ── Individual checks ──────────────────────────────────────────────────────────

def check_primary_keyword_in_h1(article: ArticleOutput, outline: ArticleOutline) -> SEOCheck:
    # Use keyword_analysis.primary_keyword (not h1_title) as the reference
    pk = article.keyword_analysis.primary_keyword.lower()
    passed = pk in article.h1.lower()
    return SEOCheck(
        check_name="primary_keyword_in_h1",
        passed=passed,
        detail=f"Primary keyword '{pk}' {'found' if passed else 'NOT found'} in H1.",
    )


def check_meta_title_length(article: ArticleOutput) -> SEOCheck:
    length = len(article.meta_title)
    passed = 50 <= length <= 60
    return SEOCheck(
        check_name="meta_title_length",
        passed=passed,
        detail=f"Meta title is {length} characters (target: 50-60).",
    )


def check_meta_description_length(article: ArticleOutput) -> SEOCheck:
    length = len(article.meta_description)
    passed = 150 <= length <= 160
    return SEOCheck(
        check_name="meta_description_length",
        passed=passed,
        detail=f"Meta description is {length} characters (target: 150-160).",
    )


def check_word_count_tolerance(article: ArticleOutput, target: int) -> SEOCheck:
    ratio = abs(article.word_count - target) / target
    passed = ratio <= 0.10
    return SEOCheck(
        check_name="word_count_within_10pct",
        passed=passed,
        detail=f"Word count {article.word_count} vs target {target} "
               f"({ratio * 100:.1f}% deviation; threshold: 10%).",
    )


def check_single_h1(article: ArticleOutput) -> SEOCheck:
    h1_count = len(re.findall(r"^# [^\n]+", article.body_markdown, re.MULTILINE))
    passed = h1_count == 1
    return SEOCheck(
        check_name="single_h1",
        passed=passed,
        detail=f"Found {h1_count} H1 heading(s) (expected exactly 1).",
    )


def check_no_h3_without_h2(article: ArticleOutput) -> SEOCheck:
    lines = article.body_markdown.split("\n")
    has_h2 = False
    violation = False
    for line in lines:
        if line.startswith("## "):
            has_h2 = True
        elif line.startswith("### ") and not has_h2:
            violation = True
            break
    passed = not violation
    return SEOCheck(
        check_name="no_h3_without_h2",
        passed=passed,
        detail="H3 heading found before any H2." if violation else "Heading hierarchy is valid.",
    )


def check_internal_links_count(article: ArticleOutput) -> SEOCheck:
    count = len(article.internal_links)
    passed = 3 <= count <= 5
    return SEOCheck(
        check_name="internal_links_count",
        passed=passed,
        detail=f"{count} internal link suggestion(s) (target: 3-5).",
    )


def check_external_references_count(article: ArticleOutput) -> SEOCheck:
    count = len(article.external_references)
    passed = 2 <= count <= 4
    return SEOCheck(
        check_name="external_references_count",
        passed=passed,
        detail=f"{count} external reference(s) (target: 2-4).",
    )


def check_keyword_density(article: ArticleOutput) -> SEOCheck:
    density = article.keyword_analysis.keyword_density
    passed = 0.005 <= density <= 0.025
    return SEOCheck(
        check_name="keyword_density",
        passed=passed,
        detail=f"Keyword density is {density:.4f} (target: 0.5%-2.5%).",
    )


def check_faq_present(article: ArticleOutput) -> SEOCheck:
    count = len(article.faq)
    passed = count >= 3
    return SEOCheck(
        check_name="faq_present",
        passed=passed,
        detail=f"{count} FAQ item(s) present (minimum: 3).",
    )


# ── Main node ─────────────────────────────────────────────────────────────────

def validate_output_node(state: ArticleState) -> dict:
    article = state.get("article_output")
    outline = state.get("outline")
    target_word_count = state.get("target_word_count", 1500)

    if not article or not outline:
        return {"error": "Missing article output or outline for validation"}

    checks: List[SEOCheck] = [
        check_primary_keyword_in_h1(article, outline),
        check_meta_title_length(article),
        check_meta_description_length(article),
        check_word_count_tolerance(article, target_word_count),
        check_single_h1(article),
        check_no_h3_without_h2(article),
        check_internal_links_count(article),
        check_external_references_count(article),
        check_keyword_density(article),
        check_faq_present(article),
    ]

    passed_count = sum(1 for c in checks if c.passed)
    overall_score = round(passed_count / len(checks) * 100)
    all_passed = passed_count == len(checks)

    validation_result = ValidationResult(
        passed=all_passed,
        checks=checks,
        overall_score=overall_score,
    )

    # Attach validation results to article output
    article.validation_results = validation_result

    return {
        "validation_result": validation_result,
        "article_output": article,
    }
