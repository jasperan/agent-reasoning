from agent_reasoning.agents.base import BaseAgent


class StandardAgent(BaseAgent):
    run_label = "Processing query: {query}"
    run_prefix = "Answer: "

    def __init__(self, model="gemma3:270m", **kwargs):
        super().__init__(model, **kwargs)
        self.name = "StandardAgent"
        self.color = "cyan"

    def stream(self, query):
        prompt = f"Question: {query}\n\nAnswer:"
        for chunk in self.client.generate(prompt):
            yield chunk
