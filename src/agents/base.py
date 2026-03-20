from abc import ABC, abstractmethod

from termcolor import colored

from src.client import OllamaClient


class BaseAgent(ABC):
    def __init__(self, model="gemma3:270m", **kwargs):
        self.client = OllamaClient(model=model)
        self.name = "BaseAgent"
        self.color = "white"
        self._debug_event = kwargs.get("_debug_event", None)
        self._debug_cancelled = False

    def _debug_pause(self):
        if self._debug_event is not None and not self._debug_cancelled:
            self._debug_event.wait()
            self._debug_event.clear()

    def log_thought(self, message):
        print(colored(f"[{self.name}]: {message}", self.color))

    @abstractmethod
    def run(self, query):
        pass

    def stream(self, query):
        """
        Default generator that yields chunks.
        Subclasses should implement this or run() to support streaming.
        If only run() is implemented, this wrapper yields the final result as one chunk.
        """
        result = self.run(query)
        if result:
            yield result
