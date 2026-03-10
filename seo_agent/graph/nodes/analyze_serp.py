"""Node 2: Analyze SERP results — extract keyword, subtopics, intent, format."""
import os
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage

from graph.state import ArticleState
from models.outline import SerpAnalysis
from prompts import analyze_serp as prompts


def _get_llm() -> ChatAnthropic:
    return ChatAnthropic(
        model="claude-sonnet-4-6",
        temperature=0,
        api_key=os.getenv("ANTHROPIC_API_KEY"),
    )


def analyze_serp_node(state: ArticleState) -> dict:
    serp_data = state["serp_data"]
    if not serp_data:
        return {"error": "No SERP data available for analysis"}

    llm = _get_llm().with_structured_output(SerpAnalysis)

    user_msg = prompts.build_user_message(
        topic=state["topic"],
        results=serp_data.results,
    )

    result: SerpAnalysis = llm.invoke([
        SystemMessage(content=prompts.SYSTEM),
        HumanMessage(content=user_msg),
    ])

    return {"serp_analysis": result}
