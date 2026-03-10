"""Node 4: Generate each article section via LLM."""
import os
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage

from graph.state import ArticleState
from prompts import generate_section as prompts


def _get_llm() -> ChatAnthropic:
    return ChatAnthropic(
        model="claude-sonnet-4-6",
        temperature=0.7,
        api_key=os.getenv("ANTHROPIC_API_KEY"),
    )


def generate_sections_node(state: ArticleState) -> dict:
    outline = state["outline"]
    analysis = state["serp_analysis"]

    if not outline or not analysis:
        return {"error": "Missing outline or analysis for section generation"}

    llm = _get_llm()
    sections: list[str] = []
    total = len(outline.sections)

    for i, section in enumerate(outline.sections):
        is_last = i == total - 1
        heading_prefix = "#" * section.heading_level

        system_msg = prompts.build_system_message(
            primary_keyword=analysis.primary_keyword,
            search_intent=analysis.search_intent,
            content_format=analysis.content_format,
            language=state.get("language", "en"),
            target_word_count=section.target_word_count,
            heading_level=section.heading_level,
        )

        # Hint LLM not to add a transition on the last section
        user_msg = prompts.build_user_message(
            heading=section.heading,
            heading_level=section.heading_level,
            description=section.description
            + ("" if not is_last else " (This is the final section — no transition needed.)"),
            keywords=section.keywords_to_include,
            target_word_count=section.target_word_count,
            primary_keyword=analysis.primary_keyword,
        )

        response = llm.invoke([
            SystemMessage(content=system_msg),
            HumanMessage(content=user_msg),
        ])

        body_text = response.content.strip()
        # Assemble: heading + body
        section_md = f"{heading_prefix} {section.heading}\n\n{body_text}"
        sections.append(section_md)

    return {"generated_sections": sections}
