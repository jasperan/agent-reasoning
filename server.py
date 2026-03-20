import asyncio
import json
import time

from fastapi import FastAPI, Request
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


@app.post("/api/generate_structured")
async def generate_structured(request: Request):
    """Structured streaming: yields StreamEvent objects as NDJSON."""
    body = await request.json()
    from fastapi.responses import JSONResponse

    model_name = body.get("model", "gemma3:latest")
    prompt = body.get("prompt", "")
    params = body.get("parameters", {})

    parts = model_name.split("+", 1)
    base_model = parts[0]
    strategy = parts[1] if len(parts) > 1 else "standard"

    agent_class = AGENT_MAP.get(strategy)
    if not agent_class:
        return JSONResponse({"error": f"Unknown strategy: {strategy}"}, status_code=400)

    try:
        agent = agent_class(model=base_model, **params)
    except TypeError:
        agent = agent_class(model=base_model)

    async def event_stream():
        try:
            if hasattr(agent, "stream_structured"):
                for event in agent.stream_structured(prompt):
                    yield json.dumps(event.to_dict()) + "\n"
            else:
                # Fallback: wrap plain text chunks as text events
                for chunk in agent.stream(prompt):
                    event_data = {
                        "event_type": "text",
                        "data": {"content": chunk},
                        "is_update": False,
                    }
                    yield json.dumps(event_data) + "\n"
            # Final done marker
            yield json.dumps({"event_type": "done", "data": {}, "is_update": False}) + "\n"
        except Exception as e:
            yield (
                json.dumps({"event_type": "error", "data": {"message": str(e)}, "is_update": False})
                + "\n"
            )

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


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
