from src.agents.base import BaseAgent
from termcolor import colored

class DecomposedAgent(BaseAgent):
    def __init__(self, model="gemma3:270m"):
        super().__init__(model)
        self.name = "DecomposedAgent"
        self.color = "red"

    def run(self, query):
        self.log_thought(f"Processing query by decomposing: {query}")
        
        # 1. Decompose
        self.log_thought("Decomposing the problem...")
        decomposition_prompt = f"Break down the following complex problem into a numbered list of simple sub-tasks.\nProblem: {query}\nProvide only the list."
        
        sub_tasks_text = ""
        for chunk in self.client.generate(decomposition_prompt):
            sub_tasks_text += chunk
        
        print(colored(f"\nSub-tasks Plan:\n{sub_tasks_text}", "light_grey"))
        
        # 2. Execute Sub-tasks
        context = ""
        lines = sub_tasks_text.split('\n')
        answers = []
        
        for line in lines:
            line = line.strip()
            if not line: continue
            # Basic cleanup to get the task
            task = line
            
            self.log_thought(f"Solving sub-task: {task}")
            # Solve with context
            solve_prompt = f"Context so far:\n{context}\n\nCurrent Task: {task}\nSolve this task efficiently."
            
            task_solution = ""
            print(colored(f"Result for '{task}': ", self.color), end="", flush=True)
            for chunk in self.client.generate(solve_prompt):
                print(colored(chunk, self.color), end="", flush=True)
                task_solution += chunk
            print()
            
            context += f"Task: {task}\nResult: {task_solution}\n"
            answers.append(task_solution)
            
        # 3. Synthesize
        self.log_thought("Synthesizing final answer...")
        synthesis_prompt = f"Original Query: {query}\n\nCompleted Sub-tasks results:\n{context}\n\nProvide the final comprehensive answer."
        
        final_response = ""
        print(colored("Final Answer: ", self.color), end="", flush=True)
        for chunk in self.client.generate(synthesis_prompt):
            print(colored(chunk, self.color), end="", flush=True)
            final_response += chunk
        print()
            
        return final_response
