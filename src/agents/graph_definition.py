from __future__ import annotations

from langgraph.graph import END, StateGraph

from src.agents.state_protocol import AgentState
from src.agents.nodes.embed_node import run_embed_node
from src.agents.nodes.eval_node import run_eval_node
from src.agents.nodes.ingest_node import run_ingest_node
from src.agents.nodes.multimodal_node import run_multimodal_node
from src.agents.nodes.plan_node import run_plan_node
from src.agents.nodes.policy_node import run_policy_node
from src.agents.nodes.simulate_node import run_simulate_node


def build_breakout_graph():
    graph = StateGraph(AgentState)
    graph.add_node("collectAgent", run_ingest_node)
    graph.add_node("multimodalAgent", run_multimodal_node)
    graph.add_node("embedAgent", run_embed_node)
    graph.add_node("evalAgent", run_eval_node)
    graph.add_node("simulateAgent", run_simulate_node)
    graph.add_node("policyAgent", run_policy_node)
    graph.add_node("planAgent", run_plan_node)
    graph.set_entry_point("collectAgent")
    graph.add_edge("collectAgent", "multimodalAgent")
    graph.add_edge("multimodalAgent", "embedAgent")
    graph.add_edge("embedAgent", "evalAgent")
    graph.add_edge("embedAgent", "simulateAgent")
    graph.add_edge("evalAgent", "policyAgent")
    graph.add_edge("simulateAgent", "policyAgent")
    graph.add_edge("policyAgent", "planAgent")
    graph.add_edge("planAgent", END)
    return graph.compile()


def run_breakout_agent(state: AgentState) -> AgentState:
    app = build_breakout_graph()
    initial_state: AgentState = {
        "trace": state.get("trace", []),
        "errors": state.get("errors", []),
        "confidence": state.get("confidence", {}),
    }
    initial_state.update(state)
    return app.invoke(initial_state)
