import asyncio
import unittest
import warnings

from pydantic_ai.a2a import AgentCard, AgentSkill

from agentic_patterns.core.doctors import A2ADoctor, A2ARecommendation, a2a_doctor


class TestA2ADoctor(unittest.IsolatedAsyncioTestCase):
    """Integration tests for A2ADoctor."""

    def setUp(self):
        loop = asyncio.get_event_loop()
        loop.slow_callback_duration = 30.0

    async def test_a2a_doctor_well_defined_card(self):
        """Test analyzing a well-defined agent card."""
        warnings.filterwarnings("ignore", category=ResourceWarning)
        card = AgentCard(
            name="DataProcessingAgent",
            description="An intelligent agent that processes and analyzes data from various sources. "
            "It can handle CSV, JSON, and XML formats, perform statistical analysis, and generate reports.",
            skills=[
                AgentSkill(
                    id="process_csv",
                    name="Process CSV",
                    description="Process a CSV file and return structured data",
                ),
                AgentSkill(
                    id="generate_report",
                    name="Generate Report",
                    description="Generate a summary report from processed data",
                ),
            ],
        )

        doctor = A2ADoctor()
        result = await doctor.analyze(card)

        self.assertIsInstance(result, A2ARecommendation)
        self.assertEqual(result.name, "DataProcessingAgent")

    async def test_a2a_doctor_poorly_defined_card(self):
        """Test analyzing a poorly-defined agent card."""
        card = AgentCard(
            name="Agent1",
            description="Does stuff",
            skills=[AgentSkill(id="do_thing", name="Do Thing")],
        )

        doctor = A2ADoctor()
        result = await doctor.analyze(card)

        self.assertIsInstance(result, A2ARecommendation)
        self.assertEqual(result.name, "Agent1")
        self.assertTrue(result.needs_improvement)

    async def test_a2a_doctor_batch(self):
        """Test analyzing multiple agent cards."""
        cards = [
            AgentCard(
                name="WellDefinedAgent",
                description="A clearly defined agent that performs specific tasks",
                skills=[AgentSkill(id="execute_task", name="Execute Task", description="Execute a predefined task")],
            ),
            AgentCard(
                name="VagueAgent",
                description="Does things",
            ),
        ]

        results = await a2a_doctor(cards, batch_size=5)

        self.assertEqual(len(results), 2)
        self.assertIsInstance(results[0], A2ARecommendation)
        self.assertIsInstance(results[1], A2ARecommendation)


if __name__ == "__main__":
    unittest.main()
