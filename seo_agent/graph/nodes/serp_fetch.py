"""Node 1: Fetch top-10 SERP results for the parsed keyword."""
from graph.state import ArticleState
from services.serp_client import fetch_serp


def serp_fetch_node(state: ArticleState) -> dict:
    topic = state["topic"]
    use_mock = state.get("use_mock", False)

    try:
        serp_data = fetch_serp(topic, use_mock=use_mock)
    except Exception as exc:
        return {"error": str(exc)}

    return {"serp_data": serp_data}
