"""Regression tests: the ``calculate`` tool must not be escapable.

``ReActAgent.perform_tool_call("calculate", ...)`` previously used
``eval(expr, {"__builtins__": {}}, allowed)``. That is not a sandbox: blanking
``__builtins__`` removes builtin *names* but leaves attribute *traversal*, so

    ().__class__.__base__.__subclasses__()

still reaches every loaded class and from there ``__globals__`` /
``__builtins__`` and arbitrary imports. This was confirmed to yield real
command output before the fix.

The pre-existing tests in ``test_edge_cases.py`` only asserted that bare
``open``/``eval``/``exec`` names are undefined, so they passed while the
sandbox was fully bypassable. These tests exercise the traversal itself.
"""
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def agent():
    with patch("agent_reasoning.agents.react.BaseAgent.__init__", return_value=None):
        from agent_reasoning.agents.react import ReActAgent

        a = ReActAgent.__new__(ReActAgent)
        a.name = "ReActAgent"
        a.color = "magenta"
        a._debug_event = None
        a._debug_cancelled = False
        a.client = MagicMock()
        return a


# --- legitimate arithmetic must keep working (no behavior regression) ---

@pytest.mark.parametrize(
    "expression,expected",
    [
        ("2 + 3", "5"),
        ("abs(-5)", "5"),
        ("max(1, 2, 3)", "3"),
        ("min(10, 5, 8)", "5"),
        ("round(3.14159, 2)", "3.14"),
        ("10 // 3", "3"),
        ("2 ** 10", "1024"),
        ("(2 + 3) * 4 - 1", "19"),
        ("7 % 3", "1"),
        ("-4 + 1", "-3"),
        ("2.5 * 4", "10.0"),
    ],
)
def test_arithmetic_still_works(agent, expression, expected):
    assert agent.perform_tool_call("calculate", expression) == expected


def test_division_returns_float_repr(agent):
    assert agent.perform_tool_call("calculate", "10 / 3") == str(10 / 3)


def test_division_by_zero_is_an_error_not_a_crash(agent):
    assert "Error" in agent.perform_tool_call("calculate", "1/0")


# --- the sandbox escape that previously succeeded ---

def test_blocks_subclasses_traversal(agent):
    """The exact escape PoC: attribute traversal to reach __import__."""
    poc = (
        "[c for c in ().__class__.__base__.__subclasses__() "
        "if c.__name__ == 'catch_warnings'][0]()._module."
        "__builtins__['__import__']('os').getcwd()"
    )
    result = agent.perform_tool_call("calculate", poc)
    assert "Error" in result


def test_blocks_attribute_access_to_dunder(agent):
    for payload in (
        "().__class__",
        "().__class__.__base__",
        "(1).__class__.__mro__",
        "abs.__class__.__bases__",
        "abs.__globals__",
        "''.__class__.__subclasses__()",
    ):
        assert "Error" in agent.perform_tool_call("calculate", payload), payload


def test_blocks_subscripting(agent):
    for payload in ("[1,2][0]", "{'a':1}['a']", "(1,2)[0]"):
        assert "Error" in agent.perform_tool_call("calculate", payload), payload


def test_blocks_call_targets_outside_whitelist(agent):
    for payload in (
        "__import__('os')",
        "open('/etc/passwd').read()",
        "eval('1+1')",
        "exec('x=1')",
        "print('hi')",
        "getattr(abs, '__class__')",
        "round.__call__(1)",
    ):
        assert "Error" in agent.perform_tool_call("calculate", payload), payload


def test_blocks_non_numeric_literals(agent):
    for payload in ("'abc'", "True", "[1,2,3]", "{'a':1}", "None"):
        assert "Error" in agent.perform_tool_call("calculate", payload), payload


def test_blocks_oversized_expression(agent):
    assert "Error" in agent.perform_tool_call("calculate", "1+" * 400 + "1")
