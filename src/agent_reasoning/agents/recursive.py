import io
import multiprocessing
import re
import sys

from termcolor import colored

from agent_reasoning.agents.base import BaseAgent


def _worker_loop(conn, env):
    """Child-process body: exec each received code block against one persistent namespace.

    Replies with ``(observation, final_answer_or_None)`` per block. ``final_answer`` is
    the ``str()`` of ``FINAL_ANSWER`` once the code has set it.
    """
    while True:
        try:
            code = conn.recv()
        except EOFError:
            return
        buffer = io.StringIO()
        sys.stdout = buffer
        try:
            exec(code, env)
            result = buffer.getvalue()
        except RecursionError as e:
            result = f"RecursionError: {e}"
        except MemoryError as e:
            result = f"MemoryError: {e}"
        except BaseException as e:  # noqa: BLE001 - a SystemExit must not kill the worker
            result = f"Error: {e}"
        finally:
            sys.stdout = sys.__stdout__
        final = None
        if "FINAL_ANSWER" in env:
            try:
                final = str(env["FINAL_ANSWER"])
            except Exception as e:
                final = f"<unprintable FINAL_ANSWER: {e}>"
        conn.send((result, final))


class _CodeWorker:
    """A forked interpreter that keeps its namespace across code blocks.

    Running the model's code in a child process gives a hard wall-clock timeout
    that works from any thread (``SIGALRM`` is main-thread only). Because the child
    keeps one namespace, functions, classes and other unpicklable values defined in
    one step stay usable in later steps. On timeout the child is killed and a fresh
    one is forked from the pristine ``env``, so the next step starts with reset state.
    """

    def __init__(self, env, timeout):
        self._env = env  # never exec'd into in this process; each fork gets a copy
        self.timeout = timeout
        self._proc = None
        self._conn = None
        self._start()

    def _start(self):
        ctx = multiprocessing.get_context("fork")
        self._conn, child_conn = ctx.Pipe(duplex=True)
        self._proc = ctx.Process(target=_worker_loop, args=(child_conn, self._env), daemon=True)
        self._proc.start()
        child_conn.close()

    def _kill(self):
        if self._proc is not None:
            if self._proc.is_alive():
                self._proc.kill()
            self._proc.join()
            self._proc = None
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def run(self, code):
        """Execute ``code``; returns ``(observation, final_answer_or_None)``."""
        try:
            self._conn.send(code)
            if self._conn.poll(self.timeout):
                return self._conn.recv()
            message = "TimeoutError: Code execution timed out (interpreter state was reset)"
        except (EOFError, OSError):
            message = "Error: code execution process exited (interpreter state was reset)"
        self._kill()
        self._start()
        return message, None

    def close(self):
        self._kill()


class RecursiveAgent(BaseAgent):
    # Hard wall-clock limit (seconds) for one code block.
    exec_timeout = 30

    def __init__(self, model="gemma3:270m", **kwargs):
        super().__init__(model, **kwargs)
        self.name = "RecursiveAgent"
        self.color = "cyan"

    def _sub_llm(self, prompt):
        """
        Helper function exposed to the REPL.
        Allows the agent to call the LLM recursively on data.
        """
        response = ""
        # Bypasses the interceptor: self.client is OllamaClient, so this is a base LLM call
        # and cannot re-trigger agent routing.
        for chunk in self.client.generate(prompt, stream=True):
            response += chunk
        return response

    run_label = "Processing query with RecursiveAgent"

    def stream(self, query):
        self.log_thought("Initializing Recursive Context.")

        # 1. Setup Environment
        # We assume the query IS the INPUT.
        env = {
            "__builtins__": {},
            "INPUT": query,
            "sub_llm": self._sub_llm,
            "print": print,
            "len": len,
            "range": range,
            "str": str,
            "int": int,
            "list": list,
            "dict": dict,
            "set": set,
            "min": min,
            "max": max,
            "sum": sum,
            "sorted": sorted,
            "enumerate": enumerate,
            # Add other safe builtins as needed
        }

        system_prompt = """You are a Python coding assistant that solves problems step by step.

RULES:
1. Write Python code in ```python ... ``` blocks
2. Use the variable INPUT which contains the user's question
3. Use sub_llm(prompt) to ask the LLM for text answers
4. Set FINAL_ANSWER = "your answer" when done (REQUIRED!)

IMPORTANT: Always end by setting FINAL_ANSWER!

Example for math problems:
Thought: I need to calculate the math expression.
```python
# The question asks: What is 2 + 3 * 4?
# Following order of operations: 3 * 4 = 12, then 2 + 12 = 14
result = 2 + 3 * 4
print(f"The answer is {result}")
FINAL_ANSWER = f"The answer is {result}"
```

Example for text questions:
Thought: I need to get an answer from the LLM.
```python
answer = sub_llm(INPUT)
FINAL_ANSWER = answer
```
"""

        messages = f"{system_prompt}\n"
        history = ""

        max_steps = 8

        worker = None
        try:
            for step in range(max_steps):
                if not self._check_budget():
                    yield f"\n{self._budget_exceeded_msg}\n"
                    break

                # Construct prompt for this step
                full_input = env["INPUT"]
                if step == 0:
                    current_prompt = f"""{messages}

    USER'S QUESTION: {full_input}

    Write Python code to answer this question. Set FINAL_ANSWER when done.

    Thought:"""
                else:
                    current_prompt = f"""{messages}

    USER'S QUESTION: {full_input}

    Previous steps:
    {history}

    Continue. Set FINAL_ANSWER when you have the answer.

    Thought:"""

                yield f"\n\n--- Step {step + 1} ---\nAgent: "

                # Stream the thought/code generation
                step_response = ""
                # We yield chunks to the user
                # Stop at "Observation:" locally if the model hallucinates it?
                # But the model might write code then "Observation" comes from US.
                # So stopping at ```output``` or similar might be good, but let's just parse.

                for chunk in self.client.generate(
                    current_prompt, stream=True, stop=["Observation:"]
                ):
                    yield chunk
                    step_response += chunk

                # Parse code
                code_match = re.search(r"```python(.*?)```", step_response, re.DOTALL)
                if not code_match:
                    code_match = re.search(r"```(.*?)```", step_response, re.DOTALL)

                if code_match:
                    code = code_match.group(1).strip()
                    if (
                        "python" in code.lower() and len(code) < 10
                    ):  # Handle ```python\n code``` edge case parsing
                        pass  # rudimentary check

                    yield colored("\nExecuting Code...", "yellow")

                    # Execute in a persistent child process: the timeout is a hard kill that
                    # works from any thread, and the namespace survives between steps.
                    if worker is None:
                        worker = _CodeWorker(env, self.exec_timeout)
                    result, final_ans = worker.run(code)

                    obs_str = f"\nObservation:\n{result}\n"
                    yield colored(obs_str, "blue")

                    history += f"Step {step + 1}:\n{step_response}\n{obs_str}\n"

                    if final_ans is not None:
                        yield colored("\nFINAL ANSWER FOUND\n", "green")
                        yield final_ans
                        # Break the generator
                        return
                else:
                    yield colored("\nNo code block found. Ending turn.\n", "red")
                    # Append to history, maybe it's just thinking?
                    history += f"Step {step + 1}: {step_response}\n"

            yield colored("\nMax steps reached without FINAL_ANSWER.\n", "red")
        finally:
            if worker is not None:
                worker.close()
