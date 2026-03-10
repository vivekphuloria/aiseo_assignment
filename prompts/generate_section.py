SYSTEM_TEMPLATE = """\
You are an expert content writer producing one section of a long-form SEO article.

Article context:
- Primary keyword: {primary_keyword}
- Search intent: {search_intent}
- Overall article format: {content_format}
- Language: {language}

Writing rules:
- Write in a natural, expert human voice — not robotic or listy unless the format demands it.
- Use the exact primary keyword phrase ("{primary_keyword}") at least once in this section, \
placed naturally in the opening paragraph or a prominent sentence. This is required — do not paraphrase it.
- Include the section's secondary keywords naturally — never keyword-stuff.
- Word count: write between {target_word_count} and {target_word_count_max} words. \
Do not exceed {target_word_count_max} words under any circumstances.
- Use the heading provided exactly as given as your starting H{heading_level}.
- Do NOT include the heading tag in your output — output only the body text in markdown.
- If citing a source, use the format [Source Name](url).
- End the section with a natural transition if it is not the last section.\
"""

USER_TEMPLATE = """\
Section heading (H{heading_level}): {heading}
Section should cover: {description}
Primary keyword (must appear at least once, verbatim): {primary_keyword}
Secondary keywords to include: {keywords}
Target word count: {target_word_count} words (hard limit: {target_word_count_max} words)
"""


def build_system_message(
    primary_keyword: str,
    search_intent: str,
    content_format: str,
    language: str,
    target_word_count: int,
    heading_level: int,
) -> str:
    return SYSTEM_TEMPLATE.format(
        primary_keyword=primary_keyword,
        search_intent=search_intent,
        content_format=content_format,
        language=language,
        target_word_count=target_word_count,
        target_word_count_max=round(target_word_count * 1.05),
        heading_level=heading_level,
    )


def build_user_message(
    heading: str,
    heading_level: int,
    description: str,
    keywords: list[str],
    target_word_count: int,
    primary_keyword: str,
) -> str:
    return USER_TEMPLATE.format(
        heading=heading,
        heading_level=heading_level,
        description=description,
        primary_keyword=primary_keyword,
        keywords=", ".join(keywords),
        target_word_count=target_word_count,
        target_word_count_max=round(target_word_count * 1.05),
    )
