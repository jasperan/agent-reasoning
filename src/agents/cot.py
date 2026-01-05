from src.agents.base import BaseAgent
from termcolor import colored

class CoTAgent(BaseAgent):
    def __init__(self, model="gemma3:270m"):
        super().__init__(model)
        self.name = "CoTAgent"
        self.color = "blue"

    def run(self, query):
        self.log_thought(f"Processing query with Chain-of-Thought: {query}")
        print(colored("Reasoning: ", self.color), end="", flush=True)
        full_response = ""
        for chunk in self.stream(query):
             print(colored(chunk, self.color), end="", flush=True)
             full_response += chunk
        print()
        return full_response

    def stream(self, query):
        # Injecting CoT instruction
        prompt = f"Answer the following question. Think step-by-step. Break down the reasoning process before giving the final answer.\n\nQuestion: {query}"
        
        # Stream the thought process
        for chunk in self.client.generate(prompt):
            yield chunk
