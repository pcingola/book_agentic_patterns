import asyncio
import unittest

from agentic_patterns.testing.tool_mock import tool_mock


class TestToolMock(unittest.TestCase):
    """Tests for agentic_patterns.testing.tool_mock module."""

    def test_sync_function_returns_values_in_order(self):
        """Test that a mocked sync function returns values sequentially."""
        def original_func(x: int) -> int:
            return x * 2

        mocked = tool_mock(original_func, [10, 20, 30])
        self.assertEqual(mocked(1), 10)
        self.assertEqual(mocked(2), 20)
        self.assertEqual(mocked(3), 30)

    def test_async_function_returns_values_in_order(self):
        """Test that a mocked async function returns values sequentially."""
        async def original_async(x: int) -> str:
            return f"result_{x}"

        mocked = tool_mock(original_async, ["a", "b", "c"])

        result1 = asyncio.get_event_loop().run_until_complete(mocked(1))
        result2 = asyncio.get_event_loop().run_until_complete(mocked(2))
        result3 = asyncio.get_event_loop().run_until_complete(mocked(3))

        self.assertEqual(result1, "a")
        self.assertEqual(result2, "b")
        self.assertEqual(result3, "c")

    def test_raises_index_error_when_exhausted(self):
        """Test that IndexError is raised when no more return values are available."""
        def original_func() -> str:
            return "test"

        mocked = tool_mock(original_func, ["only_one"])
        mocked()
        with self.assertRaises(IndexError):
            mocked()

    def test_preserves_function_name(self):
        """Test that the mocked function preserves the original function's name."""
        def my_special_function() -> None:
            pass

        mocked = tool_mock(my_special_function, [None])
        self.assertEqual(mocked.__name__, "my_special_function")

    def test_call_count_tracks_invocations(self):
        def original_func(x: int) -> int:
            return x

        mocked = tool_mock(original_func, [1, 2, 3])
        self.assertEqual(mocked.call_count, 0)
        mocked(10)
        self.assertEqual(mocked.call_count, 1)
        mocked(20)
        mocked(30)
        self.assertEqual(mocked.call_count, 3)

    def test_was_called_property(self):
        def original_func() -> str:
            return "test"

        mocked = tool_mock(original_func, ["a", "b"])
        self.assertFalse(mocked.was_called)
        mocked()
        self.assertTrue(mocked.was_called)

    def test_call_args_list_tracks_all_calls(self):
        def original_func(x: int, y: str, flag: bool = False) -> None:
            pass

        mocked = tool_mock(original_func, [None, None, None])
        mocked(1, "a")
        mocked(2, "b", flag=True)
        mocked(3, "c")

        args_list = mocked.call_args_list
        self.assertEqual(len(args_list), 3)
        self.assertEqual(args_list[0], ((1, "a"), {}))
        self.assertEqual(args_list[1], ((2, "b"), {"flag": True}))
        self.assertEqual(args_list[2], ((3, "c"), {}))

    def test_reset_restores_initial_state(self):
        def original_func() -> int:
            return 0

        mocked = tool_mock(original_func, [1, 2])
        mocked()
        mocked()
        self.assertEqual(mocked.call_count, 2)

        mocked.reset()
        self.assertEqual(mocked.call_count, 0)
        self.assertFalse(mocked.was_called)
        self.assertEqual(mocked.call_args_list, [])
        self.assertEqual(mocked(), 1)
        self.assertEqual(mocked(), 2)

    def test_async_call_count_tracks_invocations(self):
        async def original_async(x: int) -> int:
            return x

        mocked = tool_mock(original_async, [1, 2, 3])
        self.assertEqual(mocked.call_count, 0)

        asyncio.get_event_loop().run_until_complete(mocked(10))
        self.assertEqual(mocked.call_count, 1)

        asyncio.get_event_loop().run_until_complete(mocked(20))
        asyncio.get_event_loop().run_until_complete(mocked(30))
        self.assertEqual(mocked.call_count, 3)

    def test_async_call_args_list_tracks_all_calls(self):
        async def original_async(x: int, name: str) -> None:
            pass

        mocked = tool_mock(original_async, [None, None])
        asyncio.get_event_loop().run_until_complete(mocked(1, "first"))
        asyncio.get_event_loop().run_until_complete(mocked(2, name="second"))

        args_list = mocked.call_args_list
        self.assertEqual(len(args_list), 2)
        self.assertEqual(args_list[0], ((1, "first"), {}))
        self.assertEqual(args_list[1], ((2,), {"name": "second"}))


if __name__ == "__main__":
    unittest.main()
