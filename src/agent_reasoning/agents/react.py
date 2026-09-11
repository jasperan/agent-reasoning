import ast
import re

from termcolor import colored

from agent_reasoning.agents.base import BaseAgent
from agent_reasoning.visualization.models import ReActStep, StreamEvent, TaskStatus

_MAX_EXPRESSION_LENGTH = 500


def _eval_math_node(node: ast.AST, names: dict):
    """Recursively evaluate one arithmetic AST node."""
    if isinstance(node, ast.Constant):
        # bool is a subclass of int; excluding it keeps the tool numeric.
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return node.value
        raise ValueError("only numeric literals are allowed")

    if isinstance(node, ast.Name):
        if node.id in names:
            return names[node.id]
        raise ValueError(f"unknown name: {node.id}")

    if isinstance(node, ast.UnaryOp):
        operand = _eval_math_node(node.operand, names)
        if isinstance(node.op, ast.USub):
            return -operand
        if isinstance(node.op, ast.UAdd):
            return +operand
        raise ValueError("unsupported unary operator")

    if isinstance(node, ast.BinOp):
        left = _eval_math_node(node.left, names)
        right = _eval_math_node(node.right, names)
        operations = {
            ast.Add: lambda a, b: a + b,
            ast.Sub: lambda a, b: a - b,
            ast.Mult: lambda a, b: a * b,
            ast.Div: lambda a, b: a / b,
            ast.FloorDiv: lambda a, b: a // b,
            ast.Mod: lambda a, b: a % b,
            ast.Pow: lambda a, b: a ** b,
        }
        for op_type, operation in operations.items():
            if isinstance(node.op, op_type):
                return operation(left, right)
        raise ValueError("unsupported binary operator")

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in names:
            raise ValueError("only whitelisted functions may be called")
        if node.keywords:
            raise ValueError("keyword arguments are not supported")
        return names[node.func.id](
            *[_eval_math_node(arg, names) for arg in node.args]
        )

    raise ValueError(f"unsupported expression element: {type(node).__name__}")


def _safe_math_eval(expression: str, allowed_names: dict):
    """Evaluate a pure arithmetic expression without ``eval``.

    ``eval(expr, {"__builtins__": {}}, allowed)`` is not a sandbox: removing
    builtin *names* does not remove attribute *traversal*, so
    ``().__class__.__base__.__subclasses__()`` still reaches every loaded
    class and from there ``__globals__``/``__builtins__`` and arbitrary
    imports. This walks a restricted AST instead, so attribute access and
    subscripting are unrepresentable and there is nothing to traverse.
    """
    if not isinstance(expression, str):
        raise ValueError("expression must be a string")
    if len(expression) > _MAX_EXPRESSION_LENGTH:
        raise ValueError("expression too long")

    tree = ast.parse(expression.strip(), mode="eval")
    return _eval_math_node(tree.body, allowed_names)


class ReActAgent(BaseAgent):
    def __init__(self, model="gemma3:270m", **kwargs):
        super().__init__(model, **kwargs)
        self.name = "ReActAgent"
        self.color = "magenta"

    def perform_tool_call(self, tool_name, tool_input):
        if tool_name == "calculate":
            try:
                allowed_names = {"abs": abs, "round": round, "min": min, "max": max}
                return str(_safe_math_eval(tool_input, allowed_names))
            except Exception as e:
                return f"Error calculating: {e}"

        elif tool_name == "web_search":
            # Real Web Scraping (DuckDuckGo HTML)
            try:
                import re

                import requests

                headers = {
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/91.0.4472.124 Safari/537.36"
                    )
                }
                url = "https://html.duckduckgo.com/html/"
                data = {"q": tool_input}

                resp = requests.post(url, data=data, headers=headers, timeout=10)
                html = resp.text

                snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html)
                titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', html)

                if snippets:
                    res_str = ""
                    for i in range(min(2, len(snippets))):
                        title = titles[i] if i < len(titles) else "Result"
                        clean_snip = re.sub(r"<[^>]+>", "", snippets[i])
                        clean_title = re.sub(r"<[^>]+>", "", title)
                        res_str += f"[{i + 1}] {clean_title}: {clean_snip}\n"
                    return res_str.strip()
                return "No results found via Web Search."
            except Exception as e:
                return f"Web Search Error: {e}"

        elif tool_name == "search":
            # Fallback db
            fallback_db = {
                "python": "Python 1.0 was released in 1994.",
                "python version": "Python 1.0 was released in 1994.",
                "2026": "The year 2026 is in the future.",
                "france": "France is a country in Europe. Population ~67 million.",
            }

            try:
                import requests

                url = "https://en.wikipedia.org/w/api.php"
                params = {
                    "action": "query",
                    "list": "search",
                    "srsearch": tool_input,
                    "format": "json",
                }
                resp = requests.get(url, params=params, timeout=5)
                data = resp.json()
                if "query" in data and "search" in data["query"] and data["query"]["search"]:
                    top = data["query"]["search"][0]
                    return f"Title: {top['title']}\nSnippet: {top['snippet']}"
            except Exception:
                pass

            # Detailed Fallback Check
            key = tool_input.lower()
            for k, v in fallback_db.items():
                if k in key or key in k:
                    return f"Fallback Search: {v}"

            return "No results found."

        else:
            return "Unknown tool"

    run_label = "Processing query with ReAct: {query}"

    def stream(self, query):
        """Yield text chunks for terminal streaming."""
        for event in self.stream_structured(query):
            if event.event_type == "text":
                yield event.data
            elif event.event_type == "react_step":
                step = event.data
                if step.status == TaskStatus.RUNNING and not event.is_update:
                    yield f"\n--- Step {step.step} ---\nAgent: "
                elif step.observation and event.is_update:
                    yield colored(f"\nObservation: {step.observation}\n", "blue")

    def stream_structured(self, query):
        """Structured event streaming for visualization."""
        system_prompt = """You are a Reasoning and Acting agent.
Tools:
- web_search[query]: SEARCH THE WEB. Use for ANY question about
  current events, people, companies, or news. (e.g. web_search[CEO of Google])
- calculate[expression]: Use for math. (e.g. calculate[3+3])
- search[query]: Use ONLY for definitions.

Example:
Question: Who is the CEO of Google?
Thought: I need to check current information.
Action: web_search[current CEO of Google]
Observation: Sundar Pichai is the CEO...
Final Answer: Sundar Pichai

Instructions:
1. Answer the Question.
2. triggers a tool using 'Action: tool[input]'.
3. Wait for 'Observation:' (do not generate it).
"""
        yield StreamEvent(event_type="query", data=query)
        messages = f"{system_prompt}\nQuestion: {query}\n"
        max_steps = 5

        for i in range(max_steps):
            if not self._check_budget():
                yield StreamEvent(event_type="text", data=f"\n{self._budget_exceeded_msg}\n")
                break

            step = ReActStep(step=i + 1, status=TaskStatus.RUNNING)
            yield StreamEvent(event_type="react_step", data=step)
            yield StreamEvent(event_type="text", data=f"\n--- Step {i + 1} ---\nAgent: ")

            # Stop generation at Observation: to prevent hallucinating tools output
            response_chunk = ""
            for chunk in self.client.generate(messages, stream=True, stop=["Observation:"]):
                response_chunk += chunk
                step.thought = response_chunk
                yield StreamEvent(event_type="react_step", data=step, is_update=True)
                yield StreamEvent(event_type="text", data=chunk)

            # 1. Check for Action first (prioritize tool use over hallucinated final answer)
            # Allow optional space between name and bracket like search [query]
            match = re.search(r"Action:\s*(\w+)\s*\[(.*?)\]", response_chunk, re.IGNORECASE)

            if match:
                # We found an action!
                tool_name = match.group(1).lower()
                tool_input = match.group(2)

                step.action = tool_name
                step.action_input = tool_input
                yield StreamEvent(event_type="react_step", data=step, is_update=True)

                # Update messages only up to the action
                action_full_str = match.group(0)
                idx = response_chunk.find(action_full_str)
                valid_part = response_chunk[: idx + len(action_full_str)]
                messages = (
                    messages[: -len(response_chunk)] + valid_part if response_chunk else messages
                )

                yield StreamEvent(event_type="text", data=f"\nRunning {tool_name}...")
                observation = self.perform_tool_call(tool_name, tool_input)

                step.observation = observation
                step.status = TaskStatus.COMPLETED
                yield StreamEvent(event_type="react_step", data=step, is_update=True)

                obs_str = f"\nObservation: {observation}\n"
                yield StreamEvent(event_type="text", data=obs_str)
                messages += obs_str
                continue

            # 2. If no action, check for final answer
            if "Final Answer:" in response_chunk:
                step.status = TaskStatus.COMPLETED
                yield StreamEvent(event_type="react_step", data=step, is_update=True)

                # Extract final answer
                final_match = re.search(
                    r"Final Answer:\s*(.*)", response_chunk, re.IGNORECASE | re.DOTALL
                )
                final_answer = final_match.group(1).strip() if final_match else response_chunk
                yield StreamEvent(event_type="final", data=final_answer)
                return

        # If we exit the loop without finding final answer
        yield StreamEvent(event_type="final", data=response_chunk)
