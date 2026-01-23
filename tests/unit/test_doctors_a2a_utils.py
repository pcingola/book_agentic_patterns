import unittest

from agentic_patterns.core.doctors.a2a_doctor import AgentCard, _format_agent_card


class TestA2AUtils(unittest.TestCase):
    """Tests for A2A doctor utility functions and AgentCard model."""

    def test_agent_card_minimal(self):
        """Test AgentCard with only required fields."""
        card = AgentCard(name="TestAgent")
        self.assertEqual(card.name, "TestAgent")
        self.assertIsNone(card.description)
        self.assertIsNone(card.capabilities)
        self.assertIsNone(card.skills)
        self.assertIsNone(card.url)

    def test_agent_card_full(self):
        """Test AgentCard with all fields."""
        card = AgentCard(
            name="DataAgent",
            description="An agent that processes data",
            capabilities=["data_processing", "analysis"],
            skills=[{"id": "process", "description": "Process data"}],
            url="http://localhost:8001/.well-known/agent.json",
        )
        self.assertEqual(card.name, "DataAgent")
        self.assertEqual(card.description, "An agent that processes data")
        self.assertEqual(card.capabilities, ["data_processing", "analysis"])
        self.assertEqual(len(card.skills), 1)
        self.assertEqual(card.url, "http://localhost:8001/.well-known/agent.json")

    def test_format_agent_card_minimal(self):
        """Test formatting agent card with minimal fields."""
        card = AgentCard(name="MinimalAgent")
        result = _format_agent_card(card)

        self.assertIn("### Agent: MinimalAgent", result)
        self.assertNotIn("URL:", result)
        self.assertNotIn("Description:", result)
        self.assertNotIn("Capabilities:", result)
        self.assertNotIn("Skills:", result)

    def test_format_agent_card_with_url(self):
        """Test formatting agent card with URL."""
        card = AgentCard(name="Agent", url="http://example.com/agent.json")
        result = _format_agent_card(card)

        self.assertIn("### Agent: Agent", result)
        self.assertIn("URL: http://example.com/agent.json", result)

    def test_format_agent_card_with_description(self):
        """Test formatting agent card with description."""
        card = AgentCard(name="Agent", description="Does useful things")
        result = _format_agent_card(card)

        self.assertIn("### Agent: Agent", result)
        self.assertIn("Description: Does useful things", result)

    def test_format_agent_card_with_capabilities(self):
        """Test formatting agent card with capabilities."""
        card = AgentCard(name="Agent", capabilities=["read", "write", "execute"])
        result = _format_agent_card(card)

        self.assertIn("### Agent: Agent", result)
        self.assertIn("Capabilities: read, write, execute", result)

    def test_format_agent_card_with_skills(self):
        """Test formatting agent card with skills."""
        card = AgentCard(
            name="Agent",
            skills=[
                {"id": "search", "description": "Search documents"},
                {"id": "summarize", "description": "Summarize text"},
            ],
        )
        result = _format_agent_card(card)

        self.assertIn("### Agent: Agent", result)
        self.assertIn("Skills:", result)
        self.assertIn("search", result)
        self.assertIn("summarize", result)

    def test_format_agent_card_full(self):
        """Test formatting agent card with all fields."""
        card = AgentCard(
            name="FullAgent",
            description="A complete agent",
            capabilities=["cap1", "cap2"],
            skills=[{"id": "skill1", "input": "str"}],
            url="http://localhost:8000/agent.json",
        )
        result = _format_agent_card(card)

        self.assertIn("### Agent: FullAgent", result)
        self.assertIn("URL: http://localhost:8000/agent.json", result)
        self.assertIn("Description: A complete agent", result)
        self.assertIn("Capabilities: cap1, cap2", result)
        self.assertIn("Skills:", result)
        self.assertIn("skill1", result)


if __name__ == "__main__":
    unittest.main()
