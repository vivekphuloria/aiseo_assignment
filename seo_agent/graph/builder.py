"""Assemble the LangGraph pipeline."""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from graph.state import ArticleState
from graph.nodes.serp_fetch import serp_fetch_node
from graph.nodes.analyze_serp import analyze_serp_node
from graph.nodes.build_outline import build_outline_node
from graph.nodes.generate_sections import generate_sections_node
from graph.nodes.postprocess import postprocess_node
from graph.nodes.validate_output import validate_output_node


def build_graph(checkpointer: AsyncSqliteSaver):
    builder = StateGraph(ArticleState)

    builder.add_node("serp_fetch", serp_fetch_node)
    builder.add_node("analyze_serp", analyze_serp_node)
    builder.add_node("build_outline", build_outline_node)
    builder.add_node("generate_sections", generate_sections_node)
    builder.add_node("postprocess", postprocess_node)
    builder.add_node("validate_output", validate_output_node)

    builder.set_entry_point("serp_fetch")

    builder.add_edge("serp_fetch", "analyze_serp")
    builder.add_edge("analyze_serp", "build_outline")
    builder.add_edge("build_outline", "generate_sections")
    builder.add_edge("generate_sections", "postprocess")
    builder.add_edge("postprocess", "validate_output")
    builder.add_edge("validate_output", END)

    # EXTENSION POINT — future revision loop:
    # builder.add_conditional_edges(
    #     "validate_output",
    #     should_revise,
    #     {"revise": "generate_sections", "done": END}
    # )

    return builder.compile(checkpointer=checkpointer)
