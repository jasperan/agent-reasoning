from src.agents.base import BaseAgent
from termcolor import colored

class SelfReflectionAgent(BaseAgent):
    def __init__(self, model="gemma3:270m"):
        super().__init__(model)
        self.name = "SelfReflectionAgent"
        self.color = "green"

    def run(self, query):
        # For legacy run, we just consume the stream but might want to print the internal thoughts that are yielded
        # The stream() below will yield everything including "Initial Draft: ..." so we can just print it.
        self.log_thought(f"Processing query with Self-Reflection: {query}")
        full_response = ""
        for chunk in self.stream(query):
             # We might want to colorize based on content, but for now just print
             print(colored(chunk, self.color), end="", flush=True)
             full_response += chunk
        print()
        return full_response

    def stream(self, query):
        # 1. Initial Attempt
        yield "[Drafting initial response...]\n"
        initial_prompt = f"Answer the following question: {query}"
        initial_response = ""
        
        yield "Initial Draft: "
        for chunk in self.client.generate(initial_prompt):
             initial_response += chunk
             yield chunk
        yield "\n\n"

        # 2. Critique/Reflection
        yield "[Reflecting on the draft...]\n"
        critique_prompt = f"Review the following answer to the question: '{query}'.\nAnswer: '{initial_response}'.\nCheck for errors, logical inconsistencies, or missing information. Provide a critique of the logic."
        critique = ""
        
        yield "Critique: "
        for chunk in self.client.generate(critique_prompt):
            critique += chunk
            yield chunk
        yield "\n\n"

        # 3. Final Answer
        yield "[Generating final improved answer...]\n"
        final_prompt = f"Original Question: {query}\nInitial Draft: {initial_response}\nCritique: {critique}\n\nBased on the critique, provide a corrected and improved final answer."
        
        yield "Final Answer: "
        for chunk in self.client.generate(final_prompt):
            yield chunk
