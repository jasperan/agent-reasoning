from src.agents.base import BaseAgent
from termcolor import colored

class LeastToMostAgent(BaseAgent):
    def __init__(self, model="gemma3:270m"):
        super().__init__(model)
        self.name = "LeastToMostAgent"
        self.color = "cyan"

    def run(self, query):
        self.log_thought(f"Processing query via Least-to-Most Prompting: {query}")

        # 1. Decomposition into sub-questions (easy to hard)
        self.log_thought("Decomposing into sub-questions (easy -> hard)...")
        decomp_prompt = f"To solve the question '{query}', list the sub-questions that need to be answered, starting from the easiest/foundational ones to the final question. Output as a numbered list."
        
        plan_text = ""
        for chunk in self.client.generate(decomp_prompt):
            plan_text += chunk
        print(colored(f"Plan:\n{plan_text}", "light_grey"))

        # 2. Sequential Solving
        sub_questions = [line.strip() for line in plan_text.split('\n') if line.strip()]
        history = ""

        for q in sub_questions:
            self.log_thought(f"Addressing: {q}")
            prompt = f"Q: {q}\nAnswer this specific question based on prior context if applicable.\nContext:\n{history}"
            
            print(colored(f"Answer: ", self.color), end="", flush=True)
            answer = ""
            for chunk in self.client.generate(prompt):
                 print(colored(chunk, self.color), end="", flush=True)
                 answer += chunk
            print()
            
            history += f"Q: {q}\nA: {answer}\n"

        return answer
