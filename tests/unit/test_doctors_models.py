import unittest

from agentic_patterns.core.doctors.models import (
    A2ARecommendation,
    ArgumentRecommendation,
    Issue,
    IssueCategory,
    IssueLevel,
    PromptRecommendation,
    Recommendation,
    SkillRecommendation,
    ToolRecommendation,
)


class TestDoctorsModels(unittest.TestCase):
    """Tests for agentic_patterns.core.doctors.models module."""

    def test_issue_level_values(self):
        """Test IssueLevel enum has expected values."""
        self.assertEqual(IssueLevel.ERROR.value, "error")
        self.assertEqual(IssueLevel.WARNING.value, "warning")
        self.assertEqual(IssueLevel.INFO.value, "info")

    def test_issue_category_values(self):
        """Test IssueCategory enum has expected values."""
        self.assertEqual(IssueCategory.NAMING.value, "naming")
        self.assertEqual(IssueCategory.DOCUMENTATION.value, "documentation")
        self.assertEqual(IssueCategory.TYPES.value, "types")
        self.assertEqual(IssueCategory.ARGUMENTS.value, "arguments")
        self.assertEqual(IssueCategory.RETURN_TYPE.value, "return_type")
        self.assertEqual(IssueCategory.CLARITY.value, "clarity")
        self.assertEqual(IssueCategory.COMPLETENESS.value, "completeness")
        self.assertEqual(IssueCategory.AMBIGUITY.value, "ambiguity")
        self.assertEqual(IssueCategory.CAPABILITIES.value, "capabilities")
        self.assertEqual(IssueCategory.ENDPOINTS.value, "endpoints")

    def test_issue_str_without_suggestion(self):
        """Test Issue __str__ without suggestion."""
        issue = Issue(
            level=IssueLevel.WARNING,
            category=IssueCategory.NAMING,
            message="Name is too short",
        )
        result = str(issue)
        self.assertIn("[warning]", result)
        self.assertIn("naming", result)
        self.assertIn("Name is too short", result)
        self.assertNotIn("->", result)

    def test_issue_str_with_suggestion(self):
        """Test Issue __str__ with suggestion."""
        issue = Issue(
            level=IssueLevel.ERROR,
            category=IssueCategory.DOCUMENTATION,
            message="Missing docstring",
            suggestion="Add a docstring describing the function purpose",
        )
        result = str(issue)
        self.assertIn("[error]", result)
        self.assertIn("documentation", result)
        self.assertIn("Missing docstring", result)
        self.assertIn("->", result)
        self.assertIn("Add a docstring", result)

    def test_argument_recommendation_str_no_issues(self):
        """Test ArgumentRecommendation __str__ with no issues."""
        arg = ArgumentRecommendation(arg_name="count", arg_type="int", issues=[])
        result = str(arg)
        self.assertIn("count", result)
        self.assertIn("int", result)
        self.assertIn("OK", result)

    def test_argument_recommendation_str_with_issues(self):
        """Test ArgumentRecommendation __str__ with issues."""
        issue = Issue(
            level=IssueLevel.WARNING,
            category=IssueCategory.NAMING,
            message="Unclear name",
        )
        arg = ArgumentRecommendation(arg_name="x", arg_type="int", issues=[issue])
        result = str(arg)
        self.assertIn("x", result)
        self.assertIn("int", result)
        self.assertIn("Unclear name", result)

    def test_recommendation_str_no_improvement(self):
        """Test Recommendation __str__ when no improvement needed."""
        rec = Recommendation(name="my_tool", needs_improvement=False, issues=[])
        result = str(rec)
        self.assertIn("my_tool", result)
        self.assertIn("OK", result)
        self.assertNotIn("NEEDS IMPROVEMENT", result)

    def test_recommendation_str_needs_improvement(self):
        """Test Recommendation __str__ when improvement needed."""
        issue = Issue(
            level=IssueLevel.ERROR,
            category=IssueCategory.DOCUMENTATION,
            message="No docs",
        )
        rec = Recommendation(name="bad_tool", needs_improvement=True, issues=[issue])
        result = str(rec)
        self.assertIn("bad_tool", result)
        self.assertIn("NEEDS IMPROVEMENT", result)
        self.assertIn("No docs", result)

    def test_tool_recommendation_str(self):
        """Test ToolRecommendation __str__ with all fields."""
        arg_issue = Issue(
            level=IssueLevel.WARNING, category=IssueCategory.NAMING, message="Unclear"
        )
        arg = ArgumentRecommendation(arg_name="x", arg_type="int", issues=[arg_issue])
        return_issue = Issue(
            level=IssueLevel.INFO,
            category=IssueCategory.RETURN_TYPE,
            message="Consider typing",
        )
        general_issue = Issue(
            level=IssueLevel.ERROR,
            category=IssueCategory.DOCUMENTATION,
            message="No docstring",
        )

        rec = ToolRecommendation(
            name="process_data",
            needs_improvement=True,
            issues=[general_issue],
            arguments=[arg],
            return_type_issues=[return_issue],
        )
        result = str(rec)
        self.assertIn("Tool: process_data", result)
        self.assertIn("NEEDS IMPROVEMENT", result)
        self.assertIn("General issues", result)
        self.assertIn("No docstring", result)
        self.assertIn("Return type issues", result)
        self.assertIn("Consider typing", result)
        self.assertIn("Argument issues", result)
        self.assertIn("Unclear", result)

    def test_prompt_recommendation_str(self):
        """Test PromptRecommendation __str__ with placeholders."""
        issue = Issue(
            level=IssueLevel.WARNING,
            category=IssueCategory.AMBIGUITY,
            message="Unclear instruction",
        )
        rec = PromptRecommendation(
            name="system_prompt.md",
            needs_improvement=True,
            issues=[issue],
            placeholders_found=["user_name", "context"],
        )
        result = str(rec)
        self.assertIn("Prompt: system_prompt.md", result)
        self.assertIn("NEEDS IMPROVEMENT", result)
        self.assertIn("Placeholders:", result)
        self.assertIn("user_name", result)
        self.assertIn("context", result)
        self.assertIn("Unclear instruction", result)

    def test_skill_recommendation_str_no_issues(self):
        """Test SkillRecommendation __str__ with no issues."""
        skill = SkillRecommendation(skill_id="search_documents", issues=[])
        result = str(skill)
        self.assertIn("search_documents", result)
        self.assertIn("OK", result)

    def test_skill_recommendation_str_with_issues(self):
        """Test SkillRecommendation __str__ with issues."""
        issue = Issue(
            level=IssueLevel.WARNING,
            category=IssueCategory.DOCUMENTATION,
            message="Missing description",
        )
        skill = SkillRecommendation(skill_id="fetch_data", issues=[issue])
        result = str(skill)
        self.assertIn("fetch_data", result)
        self.assertIn("Missing description", result)

    def test_a2a_recommendation_str(self):
        """Test A2ARecommendation __str__ with all fields."""
        skill_issue = Issue(
            level=IssueLevel.WARNING,
            category=IssueCategory.DOCUMENTATION,
            message="Unclear skill",
        )
        skill = SkillRecommendation(skill_id="process", issues=[skill_issue])
        general_issue = Issue(
            level=IssueLevel.ERROR,
            category=IssueCategory.NAMING,
            message="Generic name",
        )

        rec = A2ARecommendation(
            name="DataAgent",
            needs_improvement=True,
            issues=[general_issue],
            capabilities=["data_processing", "analysis"],
            skills=[skill],
        )
        result = str(rec)
        self.assertIn("Agent: DataAgent", result)
        self.assertIn("NEEDS IMPROVEMENT", result)
        self.assertIn("Capabilities:", result)
        self.assertIn("data_processing", result)
        self.assertIn("analysis", result)
        self.assertIn("General issues", result)
        self.assertIn("Generic name", result)
        self.assertIn("Skill issues", result)
        self.assertIn("Unclear skill", result)


if __name__ == "__main__":
    unittest.main()
