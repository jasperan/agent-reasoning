import re
from src.agents.base import BaseAgent
from termcolor import colored

class ReActAgent(BaseAgent):
    def __init__(self, model="gemma3:270m"):
        super().__init__(model)
        self.name = "ReActAgent"
        self.color = "magenta"
    
    def perform_tool_call(self, tool_name, tool_input):
        # Mock tools
        if tool_name == "calculate":
            try:
                return str(eval(tool_input))
            except:
                return "Error calculating"
        elif tool_name == "search":
            return f"Simulated search results for: {tool_input}"
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
- calculate: evaluates a mathematical expression (e.g., "3+3")
- search: simulates a web search (e.g., "population of france")

Format your response as:
Thought: <reasoning>
Action: <tool_name>[<input>]
Observation: <result>
... (repeat)
Thought: <reasoning>
Final Answer: <the final result>

Stop when you have the Final Answer.
"""
        messages = f"{system_prompt}\nQuestion: {query}\n"
        max_steps = 5
        
        for i in range(max_steps):
            yield f"\n--- Step {i+1} ---\nAgent: "
            
            response_chunk = ""
            for chunk in self.client.generate(messages, stream=True):
                 yield chunk
                 response_chunk += chunk
            
            messages += response_chunk + "\n"
            
            if "Final Answer:" in response_chunk:
                return 
            
            match = re.search(r"Action:\s*(\w+)\[(.*?)\]", response_chunk)
            if match:
                tool_name = match.group(1)
                tool_input = match.group(2)
                
                observation = self.perform_tool_call(tool_name, tool_input)
                yield f"\nObservation: {observation}\n"
                
                messages += f"Observation: {observation}\n"
            else:
                if "Action:" not in response_chunk:
                     pass
