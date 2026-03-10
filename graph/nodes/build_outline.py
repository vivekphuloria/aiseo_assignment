"""Node 3: Build full article outline with SEO constraints and linking strategy."""
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage

from graph.state import ArticleState
from models.outline import ArticleOutline
from prompts import build_outline as prompts


def _get_llm() -> ChatAnthropic:
    return ChatAnthropic(
        model="claude-sonnet-4-6",
        temperature=0.2,
    )


def _normalize_word_counts(outline: ArticleOutline, target: int) -> ArticleOutline:
    """Rescale section word budgets so they sum to the target word count."""
    total = sum(s.target_word_count for s in outline.sections)
    if total == 0:
        return outline
    scale = target / total
    for section in outline.sections:
        section.target_word_count = max(50, round(section.target_word_count * scale))
    return outline


def build_outline_node(state: ArticleState) -> dict:
    analysis = state["serp_analysis"]
    if not analysis:
        return {"error": "No SERP analysis available for outline building"}

    llm = _get_llm().with_structured_output(ArticleOutline)

    system_msg = prompts.build_system_message(
        language=state.get("language", "en"),
        primary_keyword=analysis.primary_keyword,
        target_word_count=state.get("target_word_count", 1500),
        search_intent=analysis.search_intent,
        content_format=analysis.content_format,
    )

    user_msg = prompts.build_user_message(
        topic=state["topic"],
        serp_analysis_json=analysis.model_dump_json(indent=2),
    )

    outline: ArticleOutline = llm.invoke([
        SystemMessage(content=system_msg),
        HumanMessage(content=user_msg),
    ])

    # Ensure word count budgets sum to target
    target = state.get("target_word_count", 1500)
    # Scale budgets to 93% of target — sections consistently overshoot by ~7%,
    # so this keeps the final word count within the 10% tolerance window.
    outline = _normalize_word_counts(outline, round(target * 0.93))

    return {"outline": outline}
