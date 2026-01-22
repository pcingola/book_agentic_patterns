import unittest

from agentic_patterns.core.evals.runner import PrintOptions


class TestPrintOptions(unittest.TestCase):
    """Tests for PrintOptions dataclass."""

    def test_default_values(self):
        opts = PrintOptions()
        self.assertTrue(opts.include_input)
        self.assertTrue(opts.include_output)
        self.assertFalse(opts.include_evaluator_failures)
        self.assertFalse(opts.include_reasons)

    def test_custom_values(self):
        opts = PrintOptions(include_input=False, include_reasons=True)
        self.assertFalse(opts.include_input)
        self.assertTrue(opts.include_reasons)


if __name__ == "__main__":
    unittest.main()
