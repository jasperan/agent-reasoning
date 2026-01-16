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
        prompt = f"Question: {query}\n\nInstruction: Think step-by-step to answer the question. Break down the reasoning process clearly. Provide a detailed final answer."
        
        # Stream the thought process
        for chunk in self.client.generate(prompt):
            yield chunk
