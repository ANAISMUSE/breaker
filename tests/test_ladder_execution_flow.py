from __future__ import annotations

import unittest

from src.services.simulation_service import SimulationService


class LadderExecutionFlowTests(unittest.TestCase):
    def test_plan_execute_feedback_next(self) -> None:
        service = SimulationService()
        rows = [
            {
                "user_id": "u1",
                "platform": "douyin",
                "content_id": "c1",
                "timestamp": "2026-04-14T10:00:00",
                "content_type": "video",
                "text": "AI新闻",
                "image_url": "",
                "video_url": "",
                "like": 1,
                "comment": 0,
                "share": 0,
                "duration": 30,
                "topic": "technology",
                "stance": "neutral",
                "emotion_score": 3,
                "author_id": "a1",
            }
        ]
        benchmark = {"technology": 0.25, "society": 0.25, "education": 0.25, "health": 0.25}

        plan = service.create_ladder_execution(user_id="u1", rows=rows, benchmark=benchmark)
        self.assertTrue(plan.execution_id)
        self.assertGreaterEqual(len(plan.plan_steps), 1)

        executed = service.execute_ladder_step(plan.execution_id)
        self.assertIsNotNone(executed)
        self.assertIn(executed.status, {"running", "completed"})

        feedback = service.append_ladder_feedback(plan.execution_id, 0.7, "用户接受度较高")
        self.assertIsNotNone(feedback)
        self.assertGreaterEqual(len(feedback.history), 2)

        moved = service.move_ladder_next(plan.execution_id)
        self.assertIsNotNone(moved)
        self.assertGreaterEqual(moved.current_step_index, 1)


if __name__ == "__main__":
    unittest.main()
