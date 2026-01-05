
from src.agents.base import BaseAgent
from termcolor import colored
from collections import Counter
import re

class ConsistencyAgent(BaseAgent):
    def __init__(self, model="gemma3:270m", samples=3):
        super().__init__(model)
        self.name = "ConsistencyAgent"
        self.color = "cyan"
        self.samples = samples

    def run(self, query):
        self.log_thought(f"Processing query via Self-Consistency (k={self.samples}): {query}")
        
        # 1. Generate Multiple Paths (Stochastic)
        answers = []
        full_reasoning_trace = ""
        
        for i in range(self.samples):
            # Using higher temperature for diversity
            trace = f"\n[Path {i+1}/{self.samples}]\n"
            trace_content = ""
            
            # Streaming ONLY to internal buffer/UI, not returning yet
            prompt = f"Question: {query}\nThink step-by-step to answer this question. End your answer with 'Final Answer: <answer>'."
            
            for chunk in self.client.generate(prompt, temperature=0.7, stream=True):
                trace_content += chunk
            
            trace += trace_content
            # Extract Final Answer
            match = re.search(r"Final Answer:\s*(.*)", trace_content, re.IGNORECASE)
            final_ans = match.group(1).strip() if match else "Unknown"
            answers.append(final_ans)
            
            full_reasoning_trace += trace + f"\n-> Extracted: {final_ans}\n"
            print(colored(f"  Sample {i+1}: {final_ans}", "dark_grey"))

        # 2. Majority Voting
        counter = Counter(answers)
        best_answer, count = counter.most_common(1)[0]
        
        full_reasoning_trace += f"\n[Aggregation]\nVotes: {dict(counter)}\nSelected: {best_answer}"
        
        print(colored(f"Majority Logic: {best_answer} ({count}/{self.samples} votes)", self.color))
        
        # For the final return, we can return the best answer or the full trace. 
        # Usually users want the answer, but for debugging/demo we return trace + answer.
        return f"{full_reasoning_trace}\n\nFinal Consolidated Answer: {best_answer}"

    def stream(self, query):
        # Allow streaming the full decision process
        yield f"Starting Self-Consistency with {self.samples} samples...\n"
        result = self.run(query)
        yield result
