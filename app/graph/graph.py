from langgraph.graph import END, START, StateGraph

from app.graph.nodes import (
    historical_tool_node,
    hybrid_tool_node,
    live_tool_node,
    router_node,
    synthesis_node,
    general_chat_node,
)
from app.graph.state import AgentState


def _route_selector(state: AgentState) -> str:
    if getattr(state, "intent", None) == "general_chat":
        return "general_chat"

    route = state.route_target or "clarification_needed"
    if route not in {"live_tools", "historical_rag", "hybrid", "clarification_needed"}:
        return "clarification_needed"
    return route


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("router", router_node)
    graph.add_node("general_chat", general_chat_node)
    graph.add_node("live_tool", live_tool_node)
    graph.add_node("historical_tool", historical_tool_node)
    graph.add_node("hybrid_tool", hybrid_tool_node)
    graph.add_node("synthesis", synthesis_node)

    graph.add_edge(START, "router")
    graph.add_conditional_edges(
        "router",
        _route_selector,
        {
            "general_chat": "general_chat",
            "live_tools": "live_tool",
            "historical_rag": "historical_tool",
            "hybrid": "hybrid_tool",
            "clarification_needed": "synthesis",
        },
    )
    graph.add_edge("live_tool", "synthesis")
    graph.add_edge("historical_tool", "synthesis")
    graph.add_edge("hybrid_tool", "synthesis")
    graph.add_edge("synthesis", END)
    graph.add_edge("general_chat", END)

    return graph.compile()


compiled_graph = build_graph()
