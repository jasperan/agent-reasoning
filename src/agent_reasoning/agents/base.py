from abc import ABC

from termcolor import colored

from agent_reasoning.client import OllamaClient


class BaseAgent(ABC):
    # run() behaviour, overridable per subclass:
    #   run_label   -> text shown by log_thought before streaming ("" disables it)
    #   run_prefix  -> coloured prefix printed inline before the stream (e.g. "Answer: ")
    #   run_echo    -> when True, stream chunks are printed to the terminal as they arrive
    run_label = "Processing query with {name}: {query}"
    run_prefix = None
    run_echo = True

    def __init__(self, model="gemma3:latest", base_url=None, **kwargs):
        self.client = OllamaClient(model=model, base_url=base_url)
        self.name = "BaseAgent"
        self.color = "white"
        self._debug_event = kwargs.get("_debug_event", None)
        self._debug_cancelled = False
        self.max_calls = kwargs.get("max_calls", None)
        self._call_count = 0

    def _debug_pause(self):
        """If in debug mode, pause until signaled."""
        if self._debug_event is not None and not self._debug_cancelled:
            self._debug_event.wait()
            self._debug_event.clear()

    def _validate_query(self, query):
        """Validate and normalize a query input.

        Raises ValueError if query is None. Converts non-string inputs to string.
        Returns the validated query string.
        """
        if query is None:
            raise ValueError("Query must not be None")
        if not isinstance(query, str):
            query = str(query)
        return query

    def _check_budget(self) -> bool:
        """Check if we're within call budget. Returns True if OK to proceed.

        Tolerates agents constructed via ``__new__`` (as some tests do) that
        skip ``__init__`` and therefore never set the budget attributes.
        """
        if not hasattr(self, "_call_count"):
            self._call_count = 0
        if not hasattr(self, "max_calls"):
            self.max_calls = None
        self._call_count += 1
        if self.max_calls is not None and self._call_count > self.max_calls:
            return False
        return True

    @property
    def _budget_exceeded_msg(self) -> str:
        return f"[Budget exceeded: {self._call_count}/{self.max_calls} LLM calls]"

    def log_thought(self, message):
        print(colored(f"[{self.name}]: {message}", self.color))

    def run(self, query):
        """Drive the agent's stream, optionally echoing chunks to the terminal.

        Behaviour is parameterised by the ``run_label``, ``run_prefix`` and
        ``run_echo`` class attributes so subclasses rarely need to override it.
        """
        if self.run_label:
            self.log_thought(self.run_label.format(name=self.name, query=query))
        if self.run_echo and self.run_prefix:
            print(colored(self.run_prefix, self.color), end="", flush=True)
        full_response = ""
        for chunk in self.stream(query):
            if self.run_echo:
                print(colored(chunk, self.color), end="", flush=True)
            full_response += chunk
        if self.run_echo:
            print()
        return full_response

    def stream(self, query):
        """
        Default generator that yields chunks.
        Subclasses should implement this or run() to support streaming.
        If only run() is implemented, this wrapper yields the final result as one chunk.
        """
        result = self.run(query)
        if result:
            yield result
