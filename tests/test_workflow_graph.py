from src.agents.graph_definition import run_breakout_agent
from src.config.settings import settings


def test_workflow_graph_runs_and_returns_trace() -> None:
    settings.llm_provider = "local"
    state = run_breakout_agent(
        {
            "rows": [
                {
                    "user_id": "u1",
                    "platform": "douyin",
                    "content_id": "1",
                    "timestamp": "2026-01-01T00:00:00",
                    "content_type": "video",
                    "text": "AI 科技新闻",
                    "image_url": "",
                    "video_url": "",
                    "like": 1,
                    "comment": 0,
                    "share": 0,
                    "duration": 30,
                    "topic": "technology",
                    "stance": "neutral",
                    "emotion_score": 3,
                    "author_id": "",
                }
            ],
            "benchmark": {"technology": 0.4, "education": 0.3, "society": 0.3},
            "trace": [],
            "semantic_enhanced": False,
        }
    )
    trace = state.get("trace", [])
    assert len(trace) >= 6
    assert any(item.get("agent") == "embedAgent" for item in trace)
    assert any(item.get("agent") == "evalAgent" for item in trace)
    assert any(item.get("agent") == "simulateAgent" for item in trace)
    assert "evaluation_result" in state
    assert "evaluation_meta" in state
    assert state["evaluation_meta"].get("embedding_vector_source") == "fused"
    assert "evidence" in state
    assert isinstance(state.get("evidence"), list)
    assert len(state.get("evidence", [])) >= 1
    assert "ladder_plan" in state
    assert "confidence" in state
    assert "errors" in state
