# Visualization Overhaul Design

**Date:** 2026-01-21
**Status:** Approved

## Overview

Comprehensive CLI visualization improvements for all reasoning agents, replacing flat text output with rich, structured visual displays.

## Architecture

### New Module Structure

```
src/
├── agents/
│   ├── base.py          # Add structured output methods
│   ├── tot.py           # Emit TreeNode events
│   ├── decomposed.py    # Emit SubTask events
│   ├── consistency.py   # Emit VotingSample events
│   ├── self_reflection.py # Emit ReflectionIteration events
│   ├── react.py         # Emit ReActStep events
│   ├── cot.py           # Emit ChainStep events
│   └── ...
├── visualization/       # NEW module
│   ├── __init__.py
│   ├── models.py        # Dataclasses for structured events
│   ├── base.py          # BaseVisualizer class
│   ├── tree_viz.py      # ToT nested panels
│   ├── task_viz.py      # Decomposed/LeastToMost/Recursive
│   ├── voting_viz.py    # Self-Consistency columns
│   ├── diff_viz.py      # Self-Reflection iterations
│   ├── swimlane_viz.py  # ReAct tracks
│   └── step_viz.py      # CoT numbered steps
└── agent_cli.py         # Use visualizers via registry
```

### Data Flow

```
Agent.stream(query)
  → yields structured events (TreeNode, SubTask, etc.)
  → Visualizer.render(event)
  → Rich renderable returned
  → Live.update() refreshes terminal
```

## Structured Data Models

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

# ToT - Tree of Thoughts
@dataclass
class TreeNode:
    id: str                          # e.g., "A", "A1", "B2"
    depth: int
    content: str
    score: Optional[float] = None
    parent_id: Optional[str] = None
    is_best: bool = False

# Decomposed / Least-to-Most / Recursive
@dataclass
class SubTask:
    id: int
    description: str
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    progress: float = 0.0            # 0.0 to 1.0
    parent_id: Optional[int] = None  # For nested sub-tasks

# Self-Consistency
@dataclass
class VotingSample:
    id: int
    answer: str
    reasoning: str
    votes: int = 0
    is_winner: bool = False

# Self-Reflection
@dataclass
class ReflectionIteration:
    iteration: int
    draft: str
    critique: Optional[str] = None
    improvement: Optional[str] = None
    diff_additions: list[str] = field(default_factory=list)
    diff_removals: list[str] = field(default_factory=list)

# ReAct
@dataclass
class ReActStep:
    step: int
    thought: Optional[str] = None
    action: Optional[str] = None
    action_input: Optional[str] = None
    observation: Optional[str] = None

# CoT
@dataclass
class ChainStep:
    step: int
    total_steps: Optional[int] = None
    content: str
    is_final: bool = False
```

## Visualizer Specifications

### 1. Tree of Thoughts (TreeVisualizer)

Nested Rich panels showing full tree structure with color-coded scores.

```
╭─ Query ──────────────────────────────────────────────────╮
│ "What is the best approach to solve X?"                  │
╰──────────────────────────────────────────────────────────╯
╭─ Depth 1 ────────────────────────────────────────────────╮
│ ╭─ Branch A [0.85] ──────────────────────────────╮       │
│ │ Consider the problem from angle Y...           │       │
│ │ ╭─ Branch A1 [0.72] ─────────────────────╮     │       │
│ │ │ First, we analyze component Z...       │     │       │
│ │ ╰────────────────────────────────────────╯     │       │
│ │ ╭─ Branch A2 [0.91] ★ ───────────────────╮     │       │
│ │ │ Instead, decompose into W and V...     │     │       │
│ │ ╰────────────────────────────────────────╯     │       │
│ ╰────────────────────────────────────────────────╯       │
│ ╭─ Branch B [0.65] ──────────────────────────────╮       │
│ │ Alternative: use heuristic approach...         │       │
│ │ (pruned - score below threshold)               │       │
│ ╰────────────────────────────────────────────────╯       │
╰──────────────────────────────────────────────────────────╯
```

**Color coding:**
- Green border: score >= 0.8
- Yellow border: score 0.5-0.8
- Red border: score < 0.5 (pruned, dimmed)
- Star marker on winning path

### 2. Decomposed Tasks (TaskVisualizer)

Tree with status indicators and progress bars per subtask.

```
╭─ Main Task ──────────────────────────────────────────────╮
│ "Build a recommendation system"                          │
│                                                          │
│ Progress: [████████████░░░░░░░░] 60% (3/5 tasks)         │
╰──────────────────────────────────────────────────────────╯

📋 Task Breakdown:
├── ✅ 1. Define user requirements
│       [████████████████████] 100%
│       Result: "Users need personalized suggestions..."
│
├── ✅ 2. Design data schema
│       [████████████████████] 100%
│       Result: "Tables: users, items, interactions..."
│
├── 🔄 3. Implement similarity algorithm
│       [████████████░░░░░░░░] 60%
│       Currently: "Computing cosine similarity matrix..."
│
├── ⏳ 4. Build API endpoints
│       [░░░░░░░░░░░░░░░░░░░░] 0%
│
└── ⏳ 5. Test and validate
        [░░░░░░░░░░░░░░░░░░░░] 0%
```

**Status indicators:**
- ✅ Completed (green)
- 🔄 Running (yellow)
- ⏳ Pending (dim gray)
- ❌ Failed (red)

### 3. Self-Consistency Voting (VotingVisualizer)

Side-by-side columns showing all k=5 samples with vote tallies.

```
╭─ Self-Consistency Voting (k=5) ───────────────────────────╮
│ Query: "What is 17 × 24?"                                 │
╰───────────────────────────────────────────────────────────╯

Sampling Progress: [████████████████████] 5/5 complete

┌──────────────────┬──────────────────┬──────────────────┐
│  🔵 Sample 1     │  🟢 Sample 2     │  🟣 Sample 3     │
├──────────────────┼──────────────────┼──────────────────┤
│ 17 × 24          │ 17 × 24          │ 17 × 24          │
│ = 17 × 20 + 17×4 │ = (20-3) × 24    │ = 10×24 + 7×24   │
│ = 340 + 68       │ = 480 - 72       │ = 240 + 168      │
│ = 408            │ = 408            │ = 408            │
│                  │                  │                  │
│ Final Answer:    │ Final Answer:    │ Final Answer:    │
│ 408              │ 408              │ 408              │
├──────────────────┼──────────────────┼──────────────────┤
│ 🔵 Vote: 408     │ 🟢 Vote: 408     │ 🟣 Vote: 408     │
└──────────────────┴──────────────────┴──────────────────┘

╭─ 🗳️  Voting Results ─────────────────────────────────────╮
│                                                          │
│   🟢 408  ████████████████████████████  5 votes  ✓       │
│                                                          │
│ Consensus: UNANIMOUS (100%)                              │
╰──────────────────────────────────────────────────────────╯
```

**Color scheme:**
- Distinct colors per sample: 🔵 🟢 🟣 🟠 🔴
- Green bar for winner
- Red bar for minority answers
- Yellow warnings for low consensus

### 4. Self-Reflection (DiffVisualizer)

Iteration panels with diff-highlighting between versions. Max 5 iterations.

```
╭─ Self-Reflection (max 5 iterations) ─────────────────────╮
│ Query: "Explain quantum entanglement"                    │
╰──────────────────────────────────────────────────────────╯

╭─ 📝 Iteration 1 ─────────────────────────────────────────╮
│ ┌─ Draft ──────────────────────────────────────────────┐ │
│ │ Quantum entanglement is when two particles are       │ │
│ │ connected and affect each other instantly.           │ │
│ └──────────────────────────────────────────────────────┘ │
│                                                          │
│ ┌─ 🔍 Critique ────────────────────────────────────────┐ │
│ │ • Missing: no mention of measurement correlation     │ │
│ │ • Missing: doesn't explain "spooky action"           │ │
│ │ • Imprecise: "connected" is too vague                │ │
│ └──────────────────────────────────────────────────────┘ │
│                                                          │
│ ┌─ ✏️  Refined ────────────────────────────────────────┐ │
│ │ Quantum entanglement is when two particles are       │ │
│ │ [+quantum-mechanically correlated+] such that        │ │
│ │ [+measuring one instantly determines the state+]     │ │
│ │ [+of the other, regardless of distance. Einstein+]   │ │
│ │ [+called this "spooky action at a distance."+]       │ │
│ └──────────────────────────────────────────────────────┘ │
╰──────────────────────────────────────────────────────────╯

╭─ 📊 Reflection Summary ──────────────────────────────────╮
│ Iterations: ●───●───●───●───● 5/5                        │
│ Convergence: ✅ CORRECT                                  │
│ Improvements: +42 words, -3 words, ~12 reworded          │
╰──────────────────────────────────────────────────────────╯
```

**Diff colors:**
- Green background: Added text
- Red strikethrough: Removed text
- Yellow: Modified sections

### 5. ReAct (SwimlaneVisualizer)

Three-track display for thought/action/observation. Max 5 steps.

```
╭─ ReAct Agent (Reason + Act) ─────────────────────────────╮
│ Query: "What is the population of France divided by 2?"  │
╰──────────────────────────────────────────────────────────╯

Step 1/5
┌─────────────────────┬─────────────────────┬─────────────────────┐
│ 🧠 Thought          │ 🔧 Action           │ 👁 Observation      │
├─────────────────────┼─────────────────────┼─────────────────────┤
│ I need to find the  │ web_search          │ France population   │
│ current population  │ [France population] │ ~67 million (2024)  │
│ of France first.    │                     │                     │
└─────────────────────┴─────────────────────┴─────────────────────┘
                                │
                                ▼
Step 2/5
┌─────────────────────┬─────────────────────┬─────────────────────┐
│ 🧠 Thought          │ 🔧 Action           │ 👁 Observation      │
├─────────────────────┼─────────────────────┼─────────────────────┤
│ Now I have 67M, I   │ calculate           │ 33500000            │
│ need to divide by 2 │ [67000000 / 2]      │                     │
└─────────────────────┴─────────────────────┴─────────────────────┘

╭─ 🎯 Final Answer ────────────────────────────────────────╮
│ The population of France divided by 2 is approximately   │
│ 33.5 million people.                                     │
├─ 📊 Tool Usage Summary ──────────────────────────────────┤
│ web_search: 1 call ✅  calculate: 1 call ✅              │
╰──────────────────────────────────────────────────────────╯
```

**Color scheme:**
- 🧠 Blue: Thoughts
- 🔧 Yellow: Actions
- 👁 Green: Observations
- 🔴 Red: Errors

### 6. Chain-of-Thought (StepVisualizer)

Numbered step panels with visual flow arrows.

```
╭─ Chain-of-Thought Reasoning ─────────────────────────────╮
│ Query: "If a train travels 120km in 2 hours..."          │
╰──────────────────────────────────────────────────────────╯

┌─ Step 1 ─────────────────────────────────────────────────┐
│ 🔢 First, I need to find the total distance traveled.    │
│    Total distance = 120km + 180km = 300km                │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─ Step 2 ─────────────────────────────────────────────────┐
│ ⏱️  Next, I calculate the total time taken.              │
│    Total time = 2 hours + 3 hours = 5 hours              │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
╭─ 🎯 Final Answer ────────────────────────────────────────╮
│ The average speed of the train is 60 km/h.               │
╰──────────────────────────────────────────────────────────╯

Reasoning Progress: ●───●───● 3/3
```

**Step icons:** Auto-selected based on content keywords.

## Configuration Changes

| Agent | Parameter | Old | New |
|-------|-----------|-----|-----|
| Self-Consistency | `samples` | 3 | 5 |
| Self-Reflection | `max_turns` | 3 | 5 |
| ReAct | `max_steps` | 3 | 5 |

## Visualizer Registry

```python
VISUALIZER_MAP = {
    "tot": TreeVisualizer,
    "decomposed": TaskVisualizer,
    "least_to_most": TaskVisualizer,
    "consistency": VotingVisualizer,
    "reflection": DiffVisualizer,
    "react": SwimlaneVisualizer,
    "cot": StepVisualizer,
    "standard": None,
    "recursive": TaskVisualizer,
}
```

## Backward Compatibility

- Agents support both `stream_raw(query)` (text) and `stream(query)` (structured)
- CLI auto-detects: use visualizer if available, else Markdown fallback
