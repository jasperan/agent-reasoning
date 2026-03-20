import asyncio
import json
import time

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.agent_reasoning.agent_metadata import get_agent_list

# Import unified AGENT_MAP from interceptor (single source of truth)
from src.interceptor import AGENT_MAP

app = FastAPI(title="Agent Reasoning Gateway")


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
        strategy = "standard"  # Default

    strategy = strategy.lower().strip()

    if strategy not in AGENT_MAP:
        # Fallback to standard if unknown strategy
        strategy = "standard"

    print(f"Rx Request: Model={base_model}, Strategy={strategy}")

    # 2. Instantiate Agent
    agent_class = AGENT_MAP[strategy]
    # We pass the base model requested by user to the agent
    agent = agent_class(model=base_model)

    # 3. Stream Response with timing
    async def response_generator():
        start_time = time.time()
        first_token_time = None
        chunk_count = 0
        try:
            for chunk in agent.stream(request.prompt):
                if first_token_time is None:
                    first_token_time = time.time()
                chunk_count += 1
                data = {
                    "model": request.model,
                    "created_at": "2023-01-01T00:00:00.000000Z",
                    "response": chunk,
                    "done": False,
                }
                yield json.dumps(data) + "\n"
                await asyncio.sleep(0)

            end_time = time.time()
            total_duration = int((end_time - start_time) * 1e9)
            ttft_ns = int((first_token_time - start_time) * 1e9) if first_token_time else 0

            data = {
                "model": request.model,
                "created_at": "2023-01-01T00:00:00.000000Z",
                "response": "",
                "done": True,
                "total_duration": total_duration,
                "load_duration": ttft_ns,
                "prompt_eval_count": 0,
                "eval_count": chunk_count,
            }
            yield json.dumps(data) + "\n"
        except Exception as e:
            err_data = {"response": f"\n\n[Error in Reasoning Agent: {str(e)}]", "done": True}
            yield json.dumps(err_data) + "\n"

    return StreamingResponse(response_generator(), media_type="application/x-ndjson")


@app.get("/api/tags")
async def tags():
    """Return available model+strategy combinations (Ollama-compatible)."""
    from src.agent_reasoning.agent_metadata import PRIMARY_AGENT_IDS

    strategies = sorted(s for s in PRIMARY_AGENT_IDS if s in AGENT_MAP)
    return {"models": [{"name": f"gemma3:270m+{s}"} for s in strategies]}


@app.get("/api/agents")
async def list_agents():
    """List available reasoning agents with full metadata."""
    agents = get_agent_list()
    return {"agents": agents, "count": len(agents)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
