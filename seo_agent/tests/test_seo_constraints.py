"""SEO constraint tests — run against the sample fixture and the live validation logic."""
import json
import re
from pathlib import Path

import pytest

from models.article import ArticleOutput


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_output.json"


@pytest.fixture(scope="module")
def article() -> ArticleOutput:
    with open(FIXTURE_PATH) as f:
        data = json.load(f)
    return ArticleOutput.model_validate(data)


# ── Meta tags ──────────────────────────────────────────────────────────────────

def test_meta_title_length(article: ArticleOutput):
    assert 50 <= len(article.meta_title) <= 60, (
        f"Meta title length {len(article.meta_title)} is out of range [50, 60]: '{article.meta_title}'"
    )


def test_meta_description_length(article: ArticleOutput):
    assert 150 <= len(article.meta_description) <= 160, (
        f"Meta description length {len(article.meta_description)} is out of range [150, 160]"
    )


# ── Keyword placement ──────────────────────────────────────────────────────────

def test_primary_keyword_in_h1(article: ArticleOutput):
    pk = article.keyword_analysis.primary_keyword.lower()
    assert pk in article.h1.lower(), (
        f"Primary keyword '{pk}' not found in H1: '{article.h1}'"
    )


def test_keyword_density_in_range(article: ArticleOutput):
    density = article.keyword_analysis.keyword_density
    assert 0.005 <= density <= 0.025, (
        f"Keyword density {density:.4f} is outside [0.005, 0.025]"
    )


# ── Content structure ──────────────────────────────────────────────────────────

def test_single_h1(article: ArticleOutput):
    h1_count = len(re.findall(r"^# [^\n]+", article.body_markdown, re.MULTILINE))
    assert h1_count == 1, f"Expected exactly 1 H1, found {h1_count}"


def test_no_h3_without_h2(article: ArticleOutput):
    has_h2 = False
    for line in article.body_markdown.split("\n"):
        if line.startswith("## "):
            has_h2 = True
        elif line.startswith("### ") and not has_h2:
            pytest.fail("Found H3 heading before any H2 heading — invalid hierarchy")


# ── Linking ────────────────────────────────────────────────────────────────────

def test_internal_links_count(article: ArticleOutput):
    count = len(article.internal_links)
    assert 3 <= count <= 5, f"Expected 3-5 internal links, got {count}"


def test_external_references_count(article: ArticleOutput):
    count = len(article.external_references)
    assert 2 <= count <= 4, f"Expected 2-4 external references, got {count}"


# ── FAQ ────────────────────────────────────────────────────────────────────────

def test_faq_not_empty(article: ArticleOutput):
    assert len(article.faq) >= 3, f"Expected at least 3 FAQ items, got {len(article.faq)}"


def test_faq_items_have_answers(article: ArticleOutput):
    for item in article.faq:
        assert item.question.strip(), "FAQ item has empty question"
        assert item.answer.strip(), f"FAQ item '{item.question}' has empty answer"


# ── Validation report ──────────────────────────────────────────────────────────

def test_validation_results_attached(article: ArticleOutput):
    assert article.validation_results is not None, "validation_results is not attached to ArticleOutput"


def test_validation_score_reasonable(article: ArticleOutput):
    if article.validation_results:
        assert article.validation_results.overall_score >= 70, (
            f"Overall SEO score {article.validation_results.overall_score} is below 70 — "
            f"review failing checks: {[c for c in article.validation_results.checks if not c.passed]}"
        )
