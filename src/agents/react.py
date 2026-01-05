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
                resp = requests.get(url, params=params).json()
                if "query" in resp and "search" in resp["query"] and resp["query"]["search"]:
                    # Return title and snippet of top result
                    top = resp["query"]["search"][0]
                    return f"Title: {top['title']}\nSnippet: {top['snippet']}"
                else:
                    return "No results found."
            except Exception as e:
                return f"Search Error: {e}"
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
Your goal is to answer the user question using tools if necessary.
Available tools:
- calculate[expression]: evaluates a mathematical expression (e.g., calculate[3+3])
- search[query]: searches Wikipedia for facts (e.g., search[population of france])

Format your response exactly as:
Thought: <reasoning>
Action: <tool_name>[<input>]
Observation: <result>
... (repeat as needed)
Thought: <reasoning>
Final Answer: <the final result>

IMPORTANT: 
- AFTER triggering an Action, STOP generating and wait for the Observation.
- Do NOT generate the Observation yourself.
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
            
            messages += response_chunk
            
            if "Final Answer:" in response_chunk:
                return 
            
            # Regex to find Action
            match = re.search(r"Action:\s*(\w+)\[(.*?)\]", response_chunk, re.IGNORECASE)
            if match:
                tool_name = match.group(1).lower()
                tool_input = match.group(2)
                
                yield f"\nRunning {tool_name}..."
                observation = self.perform_tool_call(tool_name, tool_input)
                obs_str = f"\nObservation: {observation}\n"
                yield colored(obs_str, "blue")
                
                messages += obs_str
            else:
                # If no action found but also no final answer, the model might be rambling or confused.
                # Use a hint to nudge it.
                if "Action:" not in response_chunk:
                     pass # It might be mid-thought if we didn't stop it, but we used stop token.
