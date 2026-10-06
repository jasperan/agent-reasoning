"""Tests for RecursiveAgent."""

from unittest.mock import MagicMock, patch

import pytest


def _make_agent():
    """Create a RecursiveAgent with mocked internals."""
    with patch("agent_reasoning.agents.recursive.BaseAgent.__init__", return_value=None):
        from agent_reasoning.agents.recursive import RecursiveAgent

        agent = RecursiveAgent.__new__(RecursiveAgent)
        agent.name = "RecursiveAgent"
        agent.color = "cyan"
        agent._debug_event = None
        agent._debug_cancelled = False
        agent.client = MagicMock()
        agent.client.generate = MagicMock(
            side_effect=lambda *args, **kwargs: iter(["Test response"])
        )
        return agent


def test_recursive_stream_yields_text():
    """stream() should yield text strings."""
    agent = _make_agent()
    # Return a code block that sets FINAL_ANSWER
    agent.client.generate = MagicMock(
        side_effect=lambda *args, **kwargs: iter(
            ['Thought: Simple question.\n```python\nFINAL_ANSWER = "hello"\n```']
        )
    )

    chunks = list(agent.stream("say hello"))
    assert len(chunks) > 0
    assert all(isinstance(c, str) for c in chunks)


def test_recursive_executes_code():
    """RecursiveAgent should execute code blocks and find FINAL_ANSWER."""
    agent = _make_agent()
    agent.client.generate = MagicMock(
        side_effect=lambda *args, **kwargs: iter(
            ['Thought: Calculate it.\n```python\nFINAL_ANSWER = "hello"\n```']
        )
    )

    chunks = list(agent.stream("say hello"))
    combined = "".join(chunks)
    # Should contain the final answer
    assert "hello" in combined
    # Should contain the "FINAL ANSWER FOUND" marker
    assert "FINAL ANSWER FOUND" in combined


def test_recursive_handles_no_code_block():
    """RecursiveAgent should handle LLM responses with no code block."""
    agent = _make_agent()
    # First call: no code block. Subsequent calls: also no code block.
    # Agent should continue through steps and eventually hit max.
    agent.client.generate = MagicMock(
        side_effect=lambda *args, **kwargs: iter(["Just some plain text thinking, no code here."])
    )

    chunks = list(agent.stream("test"))
    combined = "".join(chunks)
    # Should indicate no code block was found
    assert "No code block found" in combined


def test_recursive_max_steps():
    """RecursiveAgent should stop after max_steps (8) without FINAL_ANSWER."""
    agent = _make_agent()
    # Return code that never sets FINAL_ANSWER
    agent.client.generate = MagicMock(
        side_effect=lambda *args, **kwargs: iter(
            ["Thought: Working on it.\n```python\nx = 42\n```"]
        )
    )

    chunks = list(agent.stream("unsolvable"))
    combined = "".join(chunks)
    # Should hit the max steps message
    assert "Max steps reached" in combined
    # Should have gone through multiple steps
    assert "Step 8" in combined


def test_recursive_sub_llm():
    """_sub_llm should call client.generate and return the concatenated response."""
    agent = _make_agent()
    agent.client.generate = MagicMock(side_effect=lambda *args, **kwargs: iter(["part1", "part2"]))

    result = agent._sub_llm("test prompt")
    assert result == "part1part2"
    agent.client.generate.assert_called_once_with("test prompt", stream=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


def test_recursive_runs_code_from_worker_thread():
    """The debug server iterates agents in worker threads, where SIGALRM can't be installed."""
    import threading

    agent = _make_agent()
    agent.client.generate = MagicMock(
        side_effect=lambda *a, **kw: iter(["```python\nFINAL_ANSWER = 'forty-two'\n```"])
    )
    out = []
    t = threading.Thread(target=lambda: out.extend(agent.stream("q")))
    t.start()
    t.join(10)
    assert "FINAL ANSWER FOUND" in "".join(out)
    assert out[-1] == "forty-two"


def test_recursive_infinite_loop_times_out_from_worker_thread():
    import threading
    import time

    agent = _make_agent()
    agent.exec_timeout = 1
    agent.client.generate = MagicMock(
        side_effect=lambda *a, **kw: iter(["```python\nwhile True:\n    pass\n```"])
    )
    agent.max_calls = 1  # second step is refused so the stream ends after the timeout
    out = []
    t = threading.Thread(target=lambda: out.extend(agent.stream("q")))
    start = time.time()
    t.start()
    t.join(15)
    assert not t.is_alive()
    assert time.time() - start < 10
    assert "TimeoutError" in "".join(out)


def test_recursive_state_persists_across_steps_and_stdout_is_observed():
    agent = _make_agent()
    steps = iter(
        [
            "```python\nx = 21\nprint('hello')\n```",
            "```python\nFINAL_ANSWER = str(x * 2)\n```",
        ]
    )
    agent.client.generate = MagicMock(side_effect=lambda *a, **kw: iter([next(steps)]))
    out = "".join(agent.stream("q"))
    assert "hello" in out
    assert out.endswith("42")


def test_recursive_code_error_is_reported_not_raised():
    agent = _make_agent()
    steps = iter(["```python\n1/0\n```", "```python\nFINAL_ANSWER = 'ok'\n```"])
    agent.client.generate = MagicMock(side_effect=lambda *a, **kw: iter([next(steps)]))
    out = "".join(agent.stream("q"))
    assert "Error: division by zero" in out
    assert out.endswith("ok")


def _run_steps(agent, blocks):
    steps = iter(blocks)
    agent.client.generate = MagicMock(side_effect=lambda *a, **kw: iter([next(steps)]))
    return "".join(agent.stream("q"))


def test_recursive_function_defined_in_one_step_is_callable_later():
    agent = _make_agent()
    out = _run_steps(
        agent,
        [
            "```python\ndef g(n):\n    return n * 3\n\nh = lambda n: g(n) + 1\nk = 7\n```",
            "```python\nprint('mid')\n```",
            "```python\nFINAL_ANSWER = str(h(k))\n```",
        ],
    )
    assert out.endswith("22")


def test_recursive_timeout_resets_state_and_next_step_works():
    agent = _make_agent()
    agent.exec_timeout = 1
    out = _run_steps(
        agent,
        [
            "```python\nx = 5\n```",
            "```python\nwhile True:\n    pass\n```",
            "```python\nprint(x)\n```",
            "```python\nFINAL_ANSWER = 'alive'\n```",
        ],
    )
    assert "TimeoutError" in out and "state was reset" in out
    assert "name 'x' is not defined" in out  # the old namespace is gone
    assert out.endswith("alive")  # a fresh worker serves the following step


def test_recursive_worker_is_reaped_when_run_ends():
    import multiprocessing

    agent = _make_agent()
    before = {p.pid for p in multiprocessing.active_children()}
    _run_steps(agent, ["```python\nFINAL_ANSWER = 'done'\n```"])
    assert {p.pid for p in multiprocessing.active_children()} <= before

    # Abandoned mid-run (generator closed early) must also clean up.
    agent2 = _make_agent()
    steps = iter(["```python\ny = 1\n```", "```python\ny = 2\n```"])
    agent2.client.generate = MagicMock(side_effect=lambda *a, **kw: iter([next(steps)]))
    gen = agent2.stream("q")
    for chunk in gen:
        if "Observation" in chunk:
            break
    assert {p.pid for p in multiprocessing.active_children()} - before
    gen.close()
    assert {p.pid for p in multiprocessing.active_children()} <= before
