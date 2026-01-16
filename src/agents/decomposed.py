from src.agents.base import BaseAgent
from termcolor import colored

class DecomposedAgent(BaseAgent):
    def __init__(self, model="gemma3:270m"):
        super().__init__(model)
        self.name = "DecomposedAgent"
        self.color = "red"

    def run(self, query):
        # Default run implementation accumulating stream
        response = ""
        for chunk in self.stream(query):
            response += chunk
        return response

    def stream(self, query):
        yield f"Processing query by decomposing: {query}\n"
        
        # 1. Decompose
        yield "\n**Decomposing the problem...**\n"
        decomposition_prompt = f"Break down the following complex problem into a numbered list of simple sub-tasks.\nProblem: {query}\nProvide only the list."
        
        sub_tasks_text = ""
        for chunk in self.client.generate(decomposition_prompt):
            sub_tasks_text += chunk
        
        yield f"\n### Sub-tasks Plan:\n{sub_tasks_text}\n"
        
        # 2. Execute Sub-tasks
        context = ""
        lines = sub_tasks_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line: continue
            task = line
            
            yield f"\n**Solving sub-task:** `{task}`\n"
            yield f"Result: "
            
            # Solve with context
            solve_prompt = f"Context so far:\n{context}\n\nCurrent Task: {task}\nSolve this task efficiently."
            
            task_solution = ""
            for chunk in self.client.generate(solve_prompt):
                yield chunk
                task_solution += chunk
            yield "\n"
            
            context += f"Task: {task}\nResult: {task_solution}\n"
            
        # 3. Synthesize
        yield "\n**Synthesizing final answer...**\n"
        synthesis_prompt = f"Original Query: {query}\n\nCompleted Sub-tasks results:\n{context}\n\nProvide the final comprehensive answer."
        
        final_response = ""
        yield "### Final Answer:\n"
        for chunk in self.client.generate(synthesis_prompt):
            yield chunk
            final_response += chunk
        yield "\n"
