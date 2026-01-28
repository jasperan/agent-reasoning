# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Research implementation that transforms standard open-source LLMs (Gemma3, Llama3) into robust problem-solving agents using advanced cognitive architectures. Central thesis: "From predicting the next token to predicting the next thought."

**Tech Stack:** Python 3.10+, Ollama (local LLM), FastAPI, Uvicorn

## Development Commands

```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .

# Prerequisite
ollama pull gemma3:270m

# Running
python agent_cli.py                     # Interactive CLI with all agents
python main.py                          # Run benchmark suite
python server.py                        # Start reasoning gateway (port 8080)
python example_interceptor.py           # Python library usage example

# TUI (Go-based terminal interface)
cd tui && go build -o agent-tui . && ./agent-tui
```

## Architecture

### Component Hierarchy

```
Entry Points (CLI/Server/Library)
    ↓
ReasoningInterceptor (routing by model+strategy syntax)
    ↓
AGENT_MAP (10 agent types)
    ↓
BaseAgent (abstract class)
    ↓
OllamaClient (HTTP wrapper for localhost:11434)
```

### Key Components

**BaseAgent** (`src/agents/base.py`)
- Abstract base class for all agents
- Manages OllamaClient connection
- Defines `stream(query)` and `run(query)` interfaces
- Provides colored logging via `log_thought()`

**OllamaClient** (`src/client.py`)
- HTTP wrapper for Ollama API
- Handles streaming vs. non-streaming responses
- Configurable: temperature=0.7, top_k=40, top_p=0.9, num_predict=2048

**ReasoningInterceptor** (`src/interceptor.py`)
- Drop-in replacement for Ollama client
- Parses `"model+strategy"` naming convention (e.g., `"gemma3+tot"`)
- Routes to correct Agent via AGENT_MAP
- Supports both `generate()` and `chat()` interfaces

### Data Flow

```
User Query → ReasoningInterceptor.generate(model="gemma3+tot", prompt="...")
    → Parse: base_model="gemma3", strategy="tot"
    → agent = AGENT_MAP["tot"](model="gemma3")
    → agent.stream(prompt) → OllamaClient.generate()
    → HTTP to localhost:11434 → Stream chunks back
```

## Agent Types (10 Reasoning Strategies)

| Agent | Strategy | Use Case | Research |
|-------|----------|----------|----------|
| **StandardAgent** | Direct generation | Baseline | N/A |
| **CoTAgent** | Chain-of-Thought | Math, logic | Wei et al. (2022) |
| **ToTAgent** | Tree of Thoughts | Complex riddles | Yao et al. (2023) |
| **ReActAgent** | Reason + Act | Fact-checking | Yao et al. (2022) |
| **SelfReflectionAgent** | Draft → Critique → Refine | Creative writing | Shinn et al. (2023) |
| **ConsistencyAgent** | Self-Consistency voting | Diverse problems | Wang et al. (2022) |
| **DecomposedAgent** | Problem decomposition | Planning | Khot et al. (2022) |
| **LeastToMostAgent** | Least-to-Most | Complex reasoning | Zhou et al. (2022) |
| **RecursiveAgent** | Recursive LM (RLM) | Long-context | Author et al. (2025) |

### Agent Hyperparameters

- **ToT**: `width=2, depth=3` (branching factor and depth)
- **Consistency**: `samples=3` (voting samples)
- **SelfReflection**: `max_turns=3` (refinement iterations)
- **ReAct**: `max_steps=3` (reasoning steps), tools: web_search, calculate, search

## Implementation Patterns

### Streaming Pattern
All agents use `yield` for progressive output:
```python
def stream(self, query):
    for chunk in self.client.generate(prompt):
        yield chunk
```

### Prompt Injection Pattern
Strategies modify prompts rather than models:
```python
# CoT injects step-by-step instructions
prompt = f"Question: {query}\n\nInstruction: Think step-by-step..."
```

### Multi-Call Pattern
Complex agents make multiple LLM calls:
- ToT: Generate candidates → Evaluate → Prune
- ReflectionAgent: Draft → Critique → Improve (loop)
- ConsistencyAgent: Generate k samples → Vote

### Tool Integration Pattern
ReActAgent implements:
- Action parsing: `Action: tool[input]` regex extraction
- Tool implementations: `web_search()`, `calculate()`, `search()`
- Fallback mechanisms for tool failures

## Execution Modes

**Interactive CLI** (`agent_cli.py`)
- Menu-driven interface with Rich markdown rendering
- Arena mode: run all agents on same query for comparison
- Model selection, benchmarks, report generation

**Terminal UI** (`tui/`)
- Go-based TUI using Bubble Tea + Lipgloss
- Split layout: agent sidebar + chat panel
- Arena mode: 3x3 grid showing all agents in parallel
- Auto-starts server.py on launch
- Keybindings: `j/k` navigate, `Tab` switch focus, `Enter` submit, `Esc` cancel, `q` quit

**Python Library**
```python
from src.interceptor import ReasoningInterceptor
client = ReasoningInterceptor()
response = client.generate(model="gemma3:270m+tot", prompt="...", stream=True)
```

**Network Gateway** (`server.py`)
- FastAPI server on port 8080
- Ollama-compatible API at `/api/generate`
- Routes by `model+strategy` syntax, returns NDJSON streaming

**Benchmark** (`main.py`)
- Pre-defined task suite for philosophy, logic, planning, physics

## Configuration

**Models:**
- Default: `gemma3:270m` (270M parameter)
- Recommendation: `gemma2:9b` or `llama3` for production
- Base URL: `http://localhost:11434` (Ollama)
- Gateway: `http://localhost:8080` (server.py)

**Naming Convention:** `"base_model+strategy"` (e.g., `"gemma3:270m+tot"`)

## Key Files

- `/agent_cli.py` - Main CLI entry point (Python)
- `/tui/` - Terminal UI entry point (Go)
- `/src/interceptor.py` - Routing and AGENT_MAP registry
- `/src/client.py` - Ollama API wrapper
- `/src/agents/base.py` - Abstract base class
- `/src/agents/*.py` - 10 agent implementations
- `/server.py` - FastAPI gateway
- `/main.py` - Benchmark suite

## Adding New Agents

1. Inherit from `BaseAgent` in `src/agents/`
2. Implement `stream(query)` method
3. Register in `AGENT_MAP` in `src/interceptor.py`
4. Add to CLI menu in `agent_cli.py`

## Git Commit Preferences

- Do NOT include "Co-Authored-By: Claude" or any AI attribution in commit messages
- Keep commit messages focused solely on the changes made
