from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from src.agents.nodes.embed_node import run_embed_node
from src.agents.nodes.eval_node import run_eval_node
from src.agents.nodes.ingest_node import run_ingest_node
from src.agents.nodes.plan_node import run_plan_node


def build_breakout_graph():
    graph = StateGraph(dict)
    graph.add_node("ingest", run_ingest_node)
    graph.add_node("embed", run_embed_node)
    graph.add_node("eval", run_eval_node)
    graph.add_node("plan", run_plan_node)
    graph.set_entry_point("ingest")
    graph.add_edge("ingest", "embed")
    graph.add_edge("embed", "eval")
    graph.add_edge("eval", "plan")
    graph.add_edge("plan", END)
    return graph.compile()


def run_breakout_agent(state: dict[str, Any]) -> dict[str, Any]:
    app = build_breakout_graph()
    return app.invoke(state)
