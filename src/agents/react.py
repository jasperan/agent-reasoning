import re
from src.agents.base import BaseAgent
from termcolor import colored

class ReActAgent(BaseAgent):
    def __init__(self, model="gemma3:270m"):
        super().__init__(model)
        self.name = "ReActAgent"
        self.color = "magenta"
    
    def perform_tool_call(self, tool_name, tool_input):
        if tool_name == "calculate":
            try:
                # Safe-ish eval
                allowed_names = {"abs": abs, "round": round, "min": min, "max": max}
                return str(eval(tool_input, {"__builtins__": {}}, allowed_names))
            except Exception as e:
                return f"Error calculating: {e}"
        elif tool_name == "search":
            # Fallback db
            fallback_db = {
                "python": "Python 1.0 was released in 1994.",
                "python version": "Python 1.0 was released in 1994.",
                "2026": "The year 2026 is in the future.",
                "france": "France is a country in Europe. Population ~67 million."
            }
            
            try:
                import requests
                # Real Wikipedia API call
                url = "https://en.wikipedia.org/w/api.php"
                params = {
                    "action": "query",
                    "list": "search",
                    "srsearch": tool_input,
                    "format": "json"
                }
                resp = requests.get(url, params=params, timeout=5)
                data = resp.json()
                if "query" in data and "search" in data["query"] and data["query"]["search"]:
                    top = data["query"]["search"][0]
                    return f"Title: {top['title']}\nSnippet: {top['snippet']}"
            except:
                # If API fails for ANY reason, use fallback
                pass
            
            # Detailed Fallback Check
            key = tool_input.lower()
            for k, v in fallback_db.items():
                if k in key or key in k:
                    return f"Fallback Search: {v}"
            
            return "No results found."
        else:
            return "Unknown tool"

    def run(self, query):
        self.log_thought(f"Processing query with ReAct: {query}")
        full_res = ""
        for chunk in self.stream(query):
            print(colored(chunk, self.color), end="", flush=True)
            full_res += chunk
        print()
        return full_res

    def stream(self, query):
        system_prompt = """You are a Reasoning and Acting agent.
Tools:
- calculate[expression] (e.g. calculate[3+3])
- search[query] (e.g. search[Paris population])

Example:
Question: What is 12*12?
Thought: I need to multiply.
Action: calculate[12*12]
Observation: 144
Final Answer: 144

Instructions:
1. Answer the Question.
2. Use 'Action: tool[input]' triggers a tool.
3. Wait for 'Observation:' (do not generate it).
"""
        messages = f"{system_prompt}\nQuestion: {query}\n"
        max_steps = 7
        
        for i in range(max_steps):
            yield f"\n--- Step {i+1} ---\nAgent: "
            
            # Stop generation at Observation: to prevent hallucinating tools output
            response_chunk = ""
            for chunk in self.client.generate(messages, stream=True, stop=["Observation:"]):
                 yield chunk
                 response_chunk += chunk
            
            # 1. Check for Action first (prioritize tool use over hallucinated final answer)
            # Allow optional space between name and bracket like search [query]
            match = re.search(r"Action:\s*(\w+)\s*\[(.*?)\]", response_chunk, re.IGNORECASE)
            
            if match:
                # We found an action!
                # Even if the model continued and hallucinated Observation/Final Answer, we intercept here.
                tool_name = match.group(1).lower()
                tool_input = match.group(2)
                
                # Truncate the message history to stop at the Action
                # (We already yielded the hallucinated bits to the user stream, but for internal logic we fix it)
                # Actually, strictly we should have stopped yielding too, but we can't un-yield.
                # Ideally check chunk-by-chunk, but for now just fix the logic flow.
                
                # Update messages only up to the action
                action_full_str = match.group(0)
                # Find where this action occurred
                idx = response_chunk.find(action_full_str)
                valid_part = response_chunk[:idx + len(action_full_str)]
                
                # Reset messages tail
                # (We appended response_chunk fully in the previous step... wait, we did: messages += response_chunk)
                # Let's fix that.
                messages = messages[:-len(response_chunk)] + valid_part
                
                yield f"\nRunning {tool_name}..."
                observation = self.perform_tool_call(tool_name, tool_input)
                obs_str = f"\nObservation: {observation}\n"
                yield colored(obs_str, "blue")
                messages += obs_str
                continue # Skip Final Answer check for this turn
            
            # 2. If no action, check for final answer
            if "Final Answer:" in response_chunk:
                return
