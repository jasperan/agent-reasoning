from src.agents.base import BaseAgent
from termcolor import colored

class ToTAgent(BaseAgent):
    def __init__(self, model="gemma3:270m"):
        super().__init__(model)
        self.name = "ToTAgent"
        self.color = "magenta"
        self.width = 2
        self.depth = 3

    def run(self, query):
        self.log_thought(f"Processing query via Tree of Thoughts (BFS): {query}")
        full_response = ""
        for chunk in self.stream(query):
            print(colored(chunk, self.color), end="", flush=True)
            full_response += chunk
        print()
        return full_response

    def stream(self, query):
        yield f"Thinking via Tree of Thoughts (Depth={self.depth}, Width={self.width})...\n"
        
        current_thoughts = [""]
        
        for step in range(self.depth):
            yield f"\n[Step {step + 1}/{self.depth} - Exploring branches]\n"
            
            candidates = []
            
            # 1. Generate Candidates
            for thought_path in current_thoughts:
                prompt = f"Problem: {query}\nCurrent reasoning path:\n{thought_path}\n\nProvide {self.width} distinct possible next steps or continuations to solve this problem. Label them Option 1, Option 2, etc."
                
                response = ""
                for chunk in self.client.generate(prompt, stream=False):
                    response += chunk
                
                options = [opt for opt in response.split("Option ") if opt.strip()]
                if not options: options = [response]
                options = options[:self.width]
                
                for opt in options:
                    new_thought = thought_path + "\n" + opt.strip()
                    candidates.append(new_thought)

            # 2. Evaluate Candidates
            scored_candidates = []
            for cand in candidates:
                # Streaming the evaluation process is verbose, maybe just summary?
                # For demo, let's yield scores
                eval_prompt = f"Problem: {query}\nProposed Reasoning Path:\n{cand}\n\nRate this reasoning path from 0.0 to 1.0 based on correctness and promise. Output ONLY the number."
                
                score_str = ""
                for chunk in self.client.generate(eval_prompt, stream=False):
                    score_str += chunk
                
                try:
                    import re
                    # Match floating point numbers 0-1, or integers 0-1.
                    # Look for explicit "Score: X" first, then fallback to just finding a number.
                    match = re.search(r"Score:\s*(0\.\d+|1\.0|0|1)", score_str, re.IGNORECASE)
                    if not match:
                        match = re.search(r"\b(0\.\d+|1\.0|0|1)\b", score_str)
                    
                    score = float(match.group(1)) if match else 0.1 # Penalize unclear scores
                except:
                    score = 0.1
                
                yield f"  Path Score: {score}\n"
                scored_candidates.append((score, cand))
                
                # Show the candidate content briefly for user visibility
                # Extract just the new part
                new_part = cand.replace(thought_path, "").strip()
                preview = new_part.replace("\n", " ")[:100]
                yield f"    > Option: {preview}...\n"
            
            scored_candidates.sort(key=lambda x: x[0], reverse=True)
            current_thoughts = [x[1] for x in scored_candidates[:self.width]]

        best_thought = current_thoughts[0] if current_thoughts else "No valid path found."
        
        yield "\n[Best Logic Trace selected. Generating Final Answer]\n"
        final_prompt = f"Problem: {query}\n\nReasoning Trace:\n{best_thought}\n\nInstruction: Based on the reasoning above, provide a comprehensive and detailed final answer to the problem."
        
        system_msg = "You are a logic engine. You provide detailed, academic answers based on reasoning traces. Do not use conversational fillers like 'Okay' or 'Sure'."
        
        for chunk in self.client.generate(final_prompt, system=system_msg):
            yield chunk
