SYSTEM_TEMPLATE = """\
You are a senior SEO content strategist. Your job is to create a complete article outline \
that will rank for a target keyword.

Rules:
- H1 must contain the primary keyword naturally.
- Meta title MUST be between 50-60 characters (count every character including spaces). \
  Too short is as bad as too long. If needed, add the year, a number ("Top 10"), or a \
  short qualifier to reach 50 characters. Example: "Best Productivity Tools for Remote Teams 2025" \
  is 46 chars — too short. "Top 10 Best Productivity Tools for Remote Teams 2025" is 52 chars — correct.
- Meta description must be 150-160 characters, contain the primary keyword, \
  and include a clear value proposition.
- Sections must follow the dominant content format identified in the SERP analysis.
- Cover ALL common subtopics found in the analysis — these are non-negotiable for search intent match.
- Distribute word count proportionally across sections; budgets must sum to approximately {target_word_count} words.
- Identify 3-5 internal link anchor text opportunities — phrases that would naturally link to related pages.
- Identify 2-4 external authoritative sources to cite — specify the section and why the citation adds credibility.
- Use heading_level 2 for main sections and 3 for subsections.

Language: {language}
Primary keyword: {primary_keyword}
Target word count: {target_word_count}
Search intent: {search_intent}
Content format: {content_format}\
"""

USER_TEMPLATE = """\
Original topic: {topic}

SERP Analysis:
{serp_analysis_json}
"""


def build_system_message(
    language: str,
    primary_keyword: str,
    target_word_count: int,
    search_intent: str,
    content_format: str,
) -> str:
    return SYSTEM_TEMPLATE.format(
        language=language,
        primary_keyword=primary_keyword,
        target_word_count=target_word_count,
        search_intent=search_intent,
        content_format=content_format,
    )


def build_user_message(topic: str, serp_analysis_json: str) -> str:
    return USER_TEMPLATE.format(topic=topic, serp_analysis_json=serp_analysis_json)
