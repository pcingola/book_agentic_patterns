import asyncio
import unittest
import warnings

from fasta2a.schema import AgentCard, Skill

from agentic_patterns.core.doctors import A2ADoctor, A2ARecommendation, a2a_doctor

# PydanticAI agents create an internal async HTTP client (via OpenAI/OpenRouter
# provider) whose lifecycle is tied to the provider, not the agent. When the
# agent goes out of scope after run_agent() the underlying transport is not
# explicitly closed, causing Python to emit ResourceWarning about unclosed
# sockets. This is a known PydanticAI behavior -- the transport is cleaned up
# by GC, but the warning fires before that in tests. Filtering it here because
# there is no public API to close the provider's HTTP client from our code.
warnings.filterwarnings(
    "ignore", category=ResourceWarning, module=r"asyncio\.selector_events"
)


class TestA2ADoctor(unittest.IsolatedAsyncioTestCase):
    """Integration tests for A2ADoctor."""

    def setUp(self):
        loop = asyncio.get_event_loop()
        loop.slow_callback_duration = 30.0

    async def test_a2a_doctor_well_defined_card(self):
        """Test analyzing a well-defined agent card."""
        card = AgentCard(
            name="DataProcessingAgent",
            description="An intelligent agent that processes and analyzes data from various sources. "
            "It can handle CSV, JSON, and XML formats, perform statistical analysis, and generate reports.",
            skills=[
                Skill(
                    id="process_csv",
                    name="Process CSV",
                    description="Process a CSV file and return structured data",
                ),
                Skill(
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
            skills=[Skill(id="do_thing", name="Do Thing")],
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
                skills=[
                    Skill(
                        id="execute_task",
                        name="Execute Task",
                        description="Execute a predefined task",
                    )
                ],
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
