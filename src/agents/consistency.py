
from src.agents.base import BaseAgent
from termcolor import colored
from collections import Counter
import re

class ConsistencyAgent(BaseAgent):
    def __init__(self, model="gemma3:270m", samples=5):
        super().__init__(model)
        self.name = "ConsistencyAgent"
        self.color = "cyan"
        self.samples = samples

    def run(self, query):
        # Default run implementation accumulating stream
        response = ""
        for chunk in self.stream(query):
            response += chunk
        return response

    def stream(self, query):
        yield f"Processing query via Self-Consistency (k={self.samples}): {query}\n"
        
        # 1. Generate Multiple Paths (Stochastic)
        answers = []
        full_reasoning_trace = ""
        
        for i in range(self.samples):
            # Using higher temperature for diversity
            trace = f"\n**[Path {i+1}/{self.samples}]**\n"
            yield trace
            trace_content = ""
            
            prompt = f"Question: {query}\nThink step-by-step to answer this question. End your answer with 'Final Answer: <answer>'."
            
            for chunk in self.client.generate(prompt, temperature=0.7, stream=True):
                # We yield the chunk so it appears in real-time
                yield chunk
                trace_content += chunk
            
            # Extract Final Answer
            match = re.search(r"Final Answer:\s*(.*)", trace_content, re.IGNORECASE)
            final_ans = match.group(1).strip() if match else "Unknown"
            answers.append(final_ans)
            
            full_reasoning_trace += trace + trace_content + f"\n-> Extracted: {final_ans}\n"
            yield f"\n   -> *Extracted Answer: {final_ans}*\n"

        # 2. Majority Voting
        counter = Counter(answers)
        best_answer, count = counter.most_common(1)[0]
        
        yield "\n---\n"
        yield f"**Majority Logic:** {best_answer} ({count}/{self.samples} votes)\n"
        yield "\n**Final Consolidated Answer:**\n"
        yield best_answer
        yield "\n"
