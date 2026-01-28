import json
import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Import agents
from src.agents.standard import StandardAgent
from src.agents.cot import CoTAgent
from src.agents.self_reflection import SelfReflectionAgent
from src.agents.react import ReActAgent
from src.agents.tot import ToTAgent
from src.agents.recursive import RecursiveAgent
from src.agents.consistency import ConsistencyAgent
from src.agents.decomposed import DecomposedAgent
from src.agents.least_to_most import LeastToMostAgent

app = FastAPI(title="Agent Reasoning Gateway")

AGENT_MAP = {
    "standard": StandardAgent,
    "cot": CoTAgent,
    "reflection": SelfReflectionAgent,
    "react": ReActAgent,
    "tot": ToTAgent,
    "recursive": RecursiveAgent,
    "consistency": ConsistencyAgent,
    "decomposed": DecomposedAgent,
    "least_to_most": LeastToMostAgent,
}

class GenerateRequest(BaseModel):
    model: str
    prompt: str
    stream: bool = True
    # Other ollama fields ignored for this demo

@app.post("/api/generate")
async def generate(request: GenerateRequest):
    # 1. Parse Model String to find Strategy
    # Format: "model_name+strategy" e.g. "gemma3+cot"
    if "+" in request.model:
        base_model, strategy = request.model.split("+", 1)
    else:
        base_model = request.model
        strategy = "standard" # Default
    
    strategy = strategy.lower().strip()
    
    if strategy not in AGENT_MAP:
        # Fallback to standard if unknown strategy
        strategy = "standard"
        
    print(f"Rx Request: Model={base_model}, Strategy={strategy}")

    # 2. Instantiate Agent
    agent_class = AGENT_MAP[strategy]
    # We pass the base model requested by user to the agent
    agent = agent_class(model=base_model)
    
    # 3. Stream Response
    async def response_generator():
        try:
            # We treat the entire agent output (thoughts + answer) as the "response"
            # for the user to see what is happening.
            for chunk in agent.stream(request.prompt):
                # Format as Ollama JSON line
                data = {
                    "model": request.model,
                    "created_at": "2023-01-01T00:00:00.000000Z", # Dummy
                    "response": chunk,
                    "done": False
                }
                yield json.dumps(data) + "\n"
                # Small yield to allow async loop
                await asyncio.sleep(0)
            
            # Final done message
            data = {
                    "model": request.model,
                    "created_at": "2023-01-01T00:00:00.000000Z",
                    "response": "",
                    "done": True,
                    "total_duration": 0,
                    "load_duration": 0,
                    "prompt_eval_count": 0,
                    "eval_count": 0
            }
            yield json.dumps(data) + "\n"
        except Exception as e:
            err_data = {
                "response": f"\n\n[Error in Reasoning Agent: {str(e)}]",
                "done": True
            }
            yield json.dumps(err_data) + "\n"

    return StreamingResponse(response_generator(), media_type="application/x-ndjson")

@app.get("/api/tags")
async def tags():
    # Proxy /api/tags or just return our "virtual" models
    # For now, let's just return a list of capabilities
    return {
        "models": [
            {"name": "gemma3:270m+cot"},
            {"name": "gemma3:270m+tot"},
            {"name": "gemma3:270m+react"},
            {"name": "gemma3:270m+reflection"},
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
