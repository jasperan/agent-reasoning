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
        max_turns = 5
        current_answer = ""
        
        # 1. Initial Attempt
        yield "[Drafting initial response...]\n"
        initial_prompt = f"Answer the following question: {query}"
        
        yield "Initial Draft: "
        for chunk in self.client.generate(initial_prompt):
             current_answer += chunk
             yield chunk
        yield "\n\n"

        # 2. Reflection Loop
        for turn in range(max_turns):
            yield f"\n[Reflection Turn {turn+1}/{max_turns}]\n"
            
            # Critique
            critique_prompt = f"Review the following answer to the question: '{query}'.\nAnswer: '{current_answer}'.\nIf the answer is correct and complete, output ONLY 'CORRECT'. Otherwise, list the errors."
            critique = ""
            yield "Critique: "
            for chunk in self.client.generate(critique_prompt):
                critique += chunk
                yield chunk
            yield "\n"
            
            if "CORRECT" in critique.upper() and len(critique) < 20:
                yield colored("\n[Critique passed. Answer is correct.]\n", "green")
                break
            
            # Improvement
            yield "Refining Answer...\n"
            improvement_prompt = f"Original Question: {query}\nCurrent Answer: {current_answer}\nCritique: {critique}\n\nProvide the corrected final answer."
            
            new_answer = ""
            for chunk in self.client.generate(improvement_prompt):
                new_answer += chunk
                yield chunk
            yield "\n"
            current_answer = new_answer
        
        yield f"\nFinal Result: {current_answer}\n"
