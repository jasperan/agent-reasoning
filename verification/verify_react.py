
from src.agents.react import ReActAgent
from termcolor import colored

def test_react():
    print(colored("=== Testing ReActAgent (Reasoning + Acting) ===", "blue", attrs=["bold"]))
    agent = ReActAgent()
    
    # A question requiring outside knowledge (Python release year) and maybe simple math
    query = "When was the first version of Python released? Subtract that year from 2026."
    
    result = agent.run(query)
    
    print("\n[Done]")

if __name__ == "__main__":
    test_react()
