# Visualization Overhaul Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace flat text output with rich, structured CLI visualizations for all reasoning agents.

**Architecture:** Create a new `src/visualization/` module with dataclass models for structured events and Rich-based visualizers. Refactor agents to emit structured events via `stream_structured()` while maintaining backward compatibility with raw `stream()`. Update CLI to use visualizer registry.

**Tech Stack:** Python 3.10+, Rich (panels, tables, progress, live), dataclasses, difflib

---

## Task 1: Add Rich Dependency

**Files:**
- Modify: `requirements.txt`

**Step 1: Add rich to requirements**

```bash
echo "rich>=13.0.0" >> requirements.txt
```

**Step 2: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: Successfully installed rich

**Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore: add rich library for CLI visualization"
```

---

## Task 2: Create Data Models

**Files:**
- Create: `src/visualization/__init__.py`
- Create: `src/visualization/models.py`

**Step 1: Create visualization module init**

```python
# src/visualization/__init__.py
from .models import (
    TaskStatus,
    TreeNode,
    SubTask,
    VotingSample,
    ReflectionIteration,
    ReActStep,
    ChainStep,
    StreamEvent,
)

__all__ = [
    "TaskStatus",
    "TreeNode",
    "SubTask",
    "VotingSample",
    "ReflectionIteration",
    "ReActStep",
    "ChainStep",
    "StreamEvent",
]
```

**Step 2: Create data models**

```python
# src/visualization/models.py
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Union

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class TreeNode:
    """Tree of Thoughts node."""
    id: str
    depth: int
    content: str
    score: Optional[float] = None
    parent_id: Optional[str] = None
    is_best: bool = False
    is_pruned: bool = False

@dataclass
class SubTask:
    """Decomposed/Least-to-Most/Recursive task."""
    id: int
    description: str
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    progress: float = 0.0
    parent_id: Optional[int] = None

@dataclass
class VotingSample:
    """Self-Consistency voting sample."""
    id: int
    answer: str = ""
    reasoning: str = ""
    votes: int = 0
    is_winner: bool = False
    status: TaskStatus = TaskStatus.PENDING

@dataclass
class ReflectionIteration:
    """Self-Reflection iteration."""
    iteration: int
    draft: str = ""
    critique: Optional[str] = None
    improvement: Optional[str] = None
    is_correct: bool = False

@dataclass
class ReActStep:
    """ReAct reasoning step."""
    step: int
    thought: str = ""
    action: Optional[str] = None
    action_input: Optional[str] = None
    observation: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING

@dataclass
class ChainStep:
    """Chain-of-Thought step."""
    step: int
    content: str = ""
    total_steps: Optional[int] = None
    is_final: bool = False
    icon: str = "🔢"

@dataclass
class StreamEvent:
    """Wrapper for streaming events."""
    event_type: str  # "node", "task", "sample", "iteration", "react_step", "chain_step", "text", "final"
    data: Union[TreeNode, SubTask, VotingSample, ReflectionIteration, ReActStep, ChainStep, str]
    is_update: bool = False  # True if updating existing item
```

**Step 3: Verify module imports**

Run: `python -c "from src.visualization import TreeNode, SubTask; print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add src/visualization/
git commit -m "feat(viz): add structured data models for visualization"
```

---

## Task 3: Create Base Visualizer

**Files:**
- Create: `src/visualization/base.py`

**Step 1: Create base visualizer class**

```python
# src/visualization/base.py
from abc import ABC, abstractmethod
from typing import Any, Generator
from rich.console import Console, RenderableType
from rich.live import Live

from .models import StreamEvent

class BaseVisualizer(ABC):
    """Base class for all visualizers."""

    def __init__(self, console: Console = None):
        self.console = console or Console()
        self.state = {}

    @abstractmethod
    def render(self) -> RenderableType:
        """Return current Rich renderable for the visualization state."""
        pass

    @abstractmethod
    def update(self, event: StreamEvent) -> None:
        """Update internal state with new event."""
        pass

    def reset(self) -> None:
        """Reset visualizer state."""
        self.state = {}

    def run(self, event_stream: Generator[StreamEvent, None, None]) -> None:
        """Run visualization with live updates."""
        with Live(self.render(), console=self.console, refresh_per_second=10, vertical_overflow="visible") as live:
            for event in event_stream:
                self.update(event)
                live.update(self.render())
```

**Step 2: Verify base class**

Run: `python -c "from src.visualization.base import BaseVisualizer; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add src/visualization/base.py
git commit -m "feat(viz): add base visualizer class"
```

---

## Task 4: Create Tree Visualizer (ToT)

**Files:**
- Create: `src/visualization/tree_viz.py`

**Step 1: Create tree visualizer**

```python
# src/visualization/tree_viz.py
from typing import Dict, Optional
from rich.console import RenderableType
from rich.panel import Panel
from rich.tree import Tree
from rich.text import Text
from rich.console import Group

from .base import BaseVisualizer
from .models import StreamEvent, TreeNode

class TreeVisualizer(BaseVisualizer):
    """Visualizer for Tree of Thoughts - nested panels with color-coded scores."""

    def __init__(self, query: str = "", **kwargs):
        super().__init__(**kwargs)
        self.query = query
        self.nodes: Dict[str, TreeNode] = {}
        self.best_path: set = set()

    def _score_to_color(self, score: Optional[float]) -> str:
        if score is None:
            return "white"
        if score >= 0.8:
            return "green"
        if score >= 0.5:
            return "yellow"
        return "red"

    def _score_to_style(self, score: Optional[float], is_best: bool, is_pruned: bool) -> str:
        if is_pruned:
            return "dim red"
        if is_best:
            return "bold green"
        return self._score_to_color(score)

    def update(self, event: StreamEvent) -> None:
        if event.event_type == "node" and isinstance(event.data, TreeNode):
            node = event.data
            self.nodes[node.id] = node
            if node.is_best:
                self.best_path.add(node.id)
        elif event.event_type == "query" and isinstance(event.data, str):
            self.query = event.data

    def _build_subtree(self, parent_id: Optional[str], depth: int = 0) -> list:
        """Recursively build tree structure."""
        children = [n for n in self.nodes.values() if n.parent_id == parent_id]
        children.sort(key=lambda x: x.score or 0, reverse=True)
        return children

    def render(self) -> RenderableType:
        elements = []

        # Query panel
        if self.query:
            elements.append(Panel(
                self.query,
                title="[bold cyan]Query[/bold cyan]",
                border_style="cyan"
            ))

        if not self.nodes:
            elements.append(Text("Thinking...", style="dim italic"))
            return Group(*elements)

        # Build tree by depth
        max_depth = max((n.depth for n in self.nodes.values()), default=0)

        for depth in range(1, max_depth + 1):
            depth_nodes = [n for n in self.nodes.values() if n.depth == depth]
            if not depth_nodes:
                continue

            depth_panels = []
            for node in sorted(depth_nodes, key=lambda x: x.id):
                score_str = f"[{node.score:.2f}]" if node.score is not None else ""
                best_marker = " ★" if node.is_best else ""
                pruned_marker = " (pruned)" if node.is_pruned else ""

                style = self._score_to_style(node.score, node.is_best, node.is_pruned)
                title = f"Branch {node.id} {score_str}{best_marker}{pruned_marker}"

                content = node.content[:200] + "..." if len(node.content) > 200 else node.content

                depth_panels.append(Panel(
                    Text(content, style="dim" if node.is_pruned else ""),
                    title=f"[{style}]{title}[/{style}]",
                    border_style=style,
                    padding=(0, 1)
                ))

            elements.append(Panel(
                Group(*depth_panels),
                title=f"[bold]Depth {depth}[/bold]",
                border_style="blue"
            ))

        return Group(*elements)
```

**Step 2: Update __init__.py**

Add to `src/visualization/__init__.py`:
```python
from .base import BaseVisualizer
from .tree_viz import TreeVisualizer
```

And update `__all__` list.

**Step 3: Verify tree visualizer**

Run: `python -c "from src.visualization import TreeVisualizer; print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add src/visualization/
git commit -m "feat(viz): add tree visualizer for ToT"
```

---

## Task 5: Create Task Visualizer (Decomposed)

**Files:**
- Create: `src/visualization/task_viz.py`

**Step 1: Create task visualizer**

```python
# src/visualization/task_viz.py
from typing import Dict, List
from rich.console import RenderableType
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn, TaskID
from rich.tree import Tree
from rich.text import Text
from rich.console import Group

from .base import BaseVisualizer
from .models import StreamEvent, SubTask, TaskStatus

class TaskVisualizer(BaseVisualizer):
    """Visualizer for Decomposed/Least-to-Most - tree with status and progress bars."""

    STATUS_ICONS = {
        TaskStatus.PENDING: ("⏳", "dim"),
        TaskStatus.RUNNING: ("🔄", "yellow"),
        TaskStatus.COMPLETED: ("✅", "green"),
        TaskStatus.FAILED: ("❌", "red"),
    }

    def __init__(self, query: str = "", **kwargs):
        super().__init__(**kwargs)
        self.query = query
        self.tasks: Dict[int, SubTask] = {}

    def update(self, event: StreamEvent) -> None:
        if event.event_type == "task" and isinstance(event.data, SubTask):
            task = event.data
            self.tasks[task.id] = task
        elif event.event_type == "query" and isinstance(event.data, str):
            self.query = event.data

    def _make_progress_bar(self, progress: float, width: int = 20) -> str:
        filled = int(progress * width)
        empty = width - filled
        return f"[{'█' * filled}{'░' * empty}] {int(progress * 100)}%"

    def render(self) -> RenderableType:
        elements = []

        # Main task panel with overall progress
        completed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED)
        total = len(self.tasks) or 1
        overall_progress = completed / total

        header_content = f"{self.query}\n\nProgress: {self._make_progress_bar(overall_progress)} ({completed}/{total} tasks)"

        elements.append(Panel(
            header_content,
            title="[bold cyan]Main Task[/bold cyan]",
            border_style="cyan"
        ))

        if not self.tasks:
            elements.append(Text("Decomposing problem...", style="dim italic"))
            return Group(*elements)

        # Task tree
        tree = Tree("📋 Task Breakdown:")

        sorted_tasks = sorted(self.tasks.values(), key=lambda x: x.id)

        for task in sorted_tasks:
            icon, style = self.STATUS_ICONS.get(task.status, ("❓", "white"))

            # Task line with progress bar
            progress_bar = self._make_progress_bar(task.progress)
            task_text = Text()
            task_text.append(f"{icon} {task.id}. ", style=style)
            task_text.append(task.description)

            branch = tree.add(task_text)
            branch.add(Text(progress_bar, style=style))

            if task.result and task.status == TaskStatus.COMPLETED:
                result_preview = task.result[:100] + "..." if len(task.result) > 100 else task.result
                branch.add(Text(f"Result: {result_preview}", style="dim"))
            elif task.status == TaskStatus.RUNNING and task.result:
                branch.add(Text(f"Currently: {task.result[:50]}...", style="yellow italic"))

        elements.append(tree)

        return Group(*elements)
```

**Step 2: Update __init__.py**

Add `TaskVisualizer` to imports and `__all__`.

**Step 3: Verify task visualizer**

Run: `python -c "from src.visualization import TaskVisualizer; print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add src/visualization/
git commit -m "feat(viz): add task visualizer for decomposed reasoning"
```

---

## Task 6: Create Voting Visualizer (Self-Consistency)

**Files:**
- Create: `src/visualization/voting_viz.py`

**Step 1: Create voting visualizer**

```python
# src/visualization/voting_viz.py
from typing import Dict
from collections import Counter
from rich.console import RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.console import Group

from .base import BaseVisualizer
from .models import StreamEvent, VotingSample, TaskStatus

class VotingVisualizer(BaseVisualizer):
    """Visualizer for Self-Consistency - side-by-side columns with vote tallies."""

    SAMPLE_COLORS = ["blue", "green", "magenta", "yellow", "red"]
    SAMPLE_ICONS = ["🔵", "🟢", "🟣", "🟠", "🔴"]

    def __init__(self, query: str = "", k: int = 5, **kwargs):
        super().__init__(**kwargs)
        self.query = query
        self.k = k
        self.samples: Dict[int, VotingSample] = {}
        self.voting_complete = False

    def update(self, event: StreamEvent) -> None:
        if event.event_type == "sample" and isinstance(event.data, VotingSample):
            sample = event.data
            self.samples[sample.id] = sample
        elif event.event_type == "query" and isinstance(event.data, str):
            self.query = event.data
        elif event.event_type == "voting_complete":
            self.voting_complete = True

    def _make_progress_bar(self, current: int, total: int, width: int = 20) -> str:
        filled = int((current / total) * width) if total > 0 else 0
        empty = width - filled
        return f"[{'█' * filled}{'░' * empty}] {current}/{total}"

    def render(self) -> RenderableType:
        elements = []

        # Header
        elements.append(Panel(
            f"Query: {self.query}",
            title=f"[bold cyan]Self-Consistency Voting (k={self.k})[/bold cyan]",
            border_style="cyan"
        ))

        # Sampling progress
        completed = sum(1 for s in self.samples.values() if s.status == TaskStatus.COMPLETED)
        progress_text = f"Sampling Progress: {self._make_progress_bar(completed, self.k)} complete"
        elements.append(Text(progress_text))
        elements.append(Text(""))

        if not self.samples:
            elements.append(Text("Starting samples...", style="dim italic"))
            return Group(*elements)

        # Samples table
        table = Table(show_header=True, header_style="bold", expand=True)

        for i in range(min(len(self.samples), self.k)):
            color = self.SAMPLE_COLORS[i % len(self.SAMPLE_COLORS)]
            icon = self.SAMPLE_ICONS[i % len(self.SAMPLE_ICONS)]

            sample = self.samples.get(i + 1)
            if sample:
                status = "✅ Complete" if sample.status == TaskStatus.COMPLETED else "🔄 Streaming..."
                header = f"{icon} Sample {i + 1}\n{status}"
            else:
                header = f"{icon} Sample {i + 1}\n⏳ Pending"

            table.add_column(header, style=color, width=25)

        # Add reasoning rows
        row_data = []
        for i in range(min(len(self.samples), self.k)):
            sample = self.samples.get(i + 1)
            if sample:
                reasoning = sample.reasoning[:150] + "..." if len(sample.reasoning) > 150 else sample.reasoning
                cell = f"{reasoning}\n\nFinal Answer:\n{sample.answer}"
            else:
                cell = "(waiting)"
            row_data.append(cell)

        if row_data:
            table.add_row(*row_data)

        # Vote row
        vote_row = []
        for i in range(min(len(self.samples), self.k)):
            sample = self.samples.get(i + 1)
            icon = self.SAMPLE_ICONS[i % len(self.SAMPLE_ICONS)]
            if sample and sample.answer:
                vote_row.append(f"{icon} Vote: {sample.answer}")
            else:
                vote_row.append("")

        if vote_row:
            table.add_row(*vote_row)

        elements.append(table)

        # Voting results
        if self.voting_complete and self.samples:
            answers = [s.answer for s in self.samples.values() if s.answer]
            if answers:
                counter = Counter(answers)
                total_votes = len(answers)

                results = []
                for answer, count in counter.most_common():
                    bar_width = int((count / total_votes) * 30)
                    is_winner = count == counter.most_common(1)[0][1]
                    color = "green" if is_winner else "red"
                    marker = "✓ WINNER" if is_winner and count > total_votes / 2 else ""
                    results.append(f"[{color}]   {answer}  {'█' * bar_width}  {count} votes  {marker}[/{color}]")

                consensus = "UNANIMOUS" if len(counter) == 1 else f"MAJORITY ({counter.most_common(1)[0][1]}/{total_votes})"
                results.append(f"\nConsensus: {consensus}")

                elements.append(Panel(
                    "\n".join(results),
                    title="[bold]🗳️  Voting Results[/bold]",
                    border_style="yellow"
                ))

        return Group(*elements)
```

**Step 2: Update __init__.py**

Add `VotingVisualizer` to imports and `__all__`.

**Step 3: Verify voting visualizer**

Run: `python -c "from src.visualization import VotingVisualizer; print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add src/visualization/
git commit -m "feat(viz): add voting visualizer for self-consistency"
```

---

## Task 7: Create Diff Visualizer (Self-Reflection)

**Files:**
- Create: `src/visualization/diff_viz.py`

**Step 1: Create diff visualizer**

```python
# src/visualization/diff_viz.py
import difflib
from typing import Dict, List
from rich.console import RenderableType
from rich.panel import Panel
from rich.text import Text
from rich.console import Group

from .base import BaseVisualizer
from .models import StreamEvent, ReflectionIteration

class DiffVisualizer(BaseVisualizer):
    """Visualizer for Self-Reflection - iterations with diff highlighting."""

    def __init__(self, query: str = "", max_iterations: int = 5, **kwargs):
        super().__init__(**kwargs)
        self.query = query
        self.max_iterations = max_iterations
        self.iterations: Dict[int, ReflectionIteration] = {}
        self.current_phase = "draft"  # draft, critique, improvement

    def update(self, event: StreamEvent) -> None:
        if event.event_type == "iteration" and isinstance(event.data, ReflectionIteration):
            iteration = event.data
            self.iterations[iteration.iteration] = iteration
        elif event.event_type == "query" and isinstance(event.data, str):
            self.query = event.data
        elif event.event_type == "phase" and isinstance(event.data, str):
            self.current_phase = event.data

    def _compute_diff(self, old_text: str, new_text: str) -> Text:
        """Compute word-level diff with highlighting."""
        result = Text()

        old_words = old_text.split()
        new_words = new_text.split()

        matcher = difflib.SequenceMatcher(None, old_words, new_words)

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                result.append(" ".join(old_words[i1:i2]) + " ")
            elif tag == 'replace':
                result.append(" ".join(new_words[j1:j2]) + " ", style="bold green on dark_green")
            elif tag == 'insert':
                result.append(" ".join(new_words[j1:j2]) + " ", style="bold green on dark_green")
            elif tag == 'delete':
                pass  # Don't show deleted in final version

        return result

    def _make_iteration_progress(self) -> str:
        completed = len([i for i in self.iterations.values() if i.is_correct or i.improvement])
        dots = ["●" if i <= completed else "○" for i in range(1, self.max_iterations + 1)]
        return "───".join(dots) + f" {completed}/{self.max_iterations}"

    def render(self) -> RenderableType:
        elements = []

        # Header
        elements.append(Panel(
            f"Query: {self.query}",
            title=f"[bold cyan]Self-Reflection (max {self.max_iterations} iterations)[/bold cyan]",
            border_style="cyan"
        ))

        if not self.iterations:
            elements.append(Text("Drafting initial response...", style="dim italic"))
            return Group(*elements)

        # Render each iteration
        for i in sorted(self.iterations.keys()):
            iteration = self.iterations[i]

            iter_elements = []

            # Draft
            if iteration.draft:
                draft_text = iteration.draft[:300] + "..." if len(iteration.draft) > 300 else iteration.draft
                iter_elements.append(Panel(
                    draft_text,
                    title="[bold]Draft[/bold]",
                    border_style="blue"
                ))

            # Critique
            if iteration.critique:
                critique_text = iteration.critique[:200] + "..." if len(iteration.critique) > 200 else iteration.critique
                iter_elements.append(Panel(
                    critique_text,
                    title="[bold]🔍 Critique[/bold]",
                    border_style="yellow"
                ))

            # Improvement with diff
            if iteration.improvement:
                if i > 1 and (i - 1) in self.iterations:
                    prev = self.iterations[i - 1]
                    prev_text = prev.improvement or prev.draft
                    diff_text = self._compute_diff(prev_text, iteration.improvement)
                else:
                    diff_text = self._compute_diff(iteration.draft, iteration.improvement)

                iter_elements.append(Panel(
                    diff_text,
                    title="[bold]✏️  Refined[/bold]",
                    border_style="green"
                ))

            # Wrap iteration
            iter_title = f"📝 Iteration {i}"
            if iteration.is_correct:
                iter_title += " ✅ CORRECT"

            elements.append(Panel(
                Group(*iter_elements),
                title=f"[bold]{iter_title}[/bold]",
                border_style="green" if iteration.is_correct else "white"
            ))

        # Summary
        last_iter = self.iterations.get(max(self.iterations.keys()))
        if last_iter and last_iter.is_correct:
            elements.append(Panel(
                f"Iterations: {self._make_iteration_progress()}\nConvergence: ✅ CORRECT",
                title="[bold]📊 Reflection Summary[/bold]",
                border_style="green"
            ))

        return Group(*elements)
```

**Step 2: Update __init__.py**

Add `DiffVisualizer` to imports and `__all__`.

**Step 3: Verify diff visualizer**

Run: `python -c "from src.visualization import DiffVisualizer; print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add src/visualization/
git commit -m "feat(viz): add diff visualizer for self-reflection"
```

---

## Task 8: Create Swimlane Visualizer (ReAct)

**Files:**
- Create: `src/visualization/swimlane_viz.py`

**Step 1: Create swimlane visualizer**

```python
# src/visualization/swimlane_viz.py
from typing import Dict
from rich.console import RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.console import Group

from .base import BaseVisualizer
from .models import StreamEvent, ReActStep, TaskStatus

class SwimlaneVisualizer(BaseVisualizer):
    """Visualizer for ReAct - three-track thought/action/observation."""

    def __init__(self, query: str = "", max_steps: int = 5, **kwargs):
        super().__init__(**kwargs)
        self.query = query
        self.max_steps = max_steps
        self.steps: Dict[int, ReActStep] = {}
        self.final_answer: str = ""
        self.tool_usage: Dict[str, int] = {}

    def update(self, event: StreamEvent) -> None:
        if event.event_type == "react_step" and isinstance(event.data, ReActStep):
            step = event.data
            self.steps[step.step] = step
            if step.action:
                self.tool_usage[step.action] = self.tool_usage.get(step.action, 0) + 1
        elif event.event_type == "query" and isinstance(event.data, str):
            self.query = event.data
        elif event.event_type == "final_answer" and isinstance(event.data, str):
            self.final_answer = event.data

    def render(self) -> RenderableType:
        elements = []

        # Header
        elements.append(Panel(
            f"Query: {self.query}",
            title=f"[bold cyan]ReAct Agent (Reason + Act)[/bold cyan]",
            border_style="cyan"
        ))

        if not self.steps:
            elements.append(Text("Thinking...", style="dim italic"))
            return Group(*elements)

        # Render each step as a swimlane table
        for step_num in sorted(self.steps.keys()):
            step = self.steps[step_num]

            table = Table(show_header=True, expand=True, title=f"Step {step_num}/{self.max_steps}")
            table.add_column("🧠 Thought", style="blue", width=25)
            table.add_column("🔧 Action", style="yellow", width=20)
            table.add_column("👁 Observation", style="green", width=25)

            thought = step.thought[:100] + "..." if len(step.thought) > 100 else step.thought

            if step.action:
                action = f"{step.action}\n[{step.action_input}]"
            else:
                action = "─"

            if step.observation:
                obs = step.observation[:100] + "..." if len(step.observation) > 100 else step.observation
            elif step.status == TaskStatus.RUNNING:
                obs = "⏳ Waiting..."
            else:
                obs = "─"

            table.add_row(thought, action, obs)
            elements.append(table)

            # Arrow between steps
            if step_num < max(self.steps.keys()):
                elements.append(Text("                    │\n                    ▼", style="dim"))

        # Final answer
        if self.final_answer:
            tool_summary = "  ".join([f"{tool}: {count} call{'s' if count > 1 else ''} ✅"
                                      for tool, count in self.tool_usage.items()])

            elements.append(Panel(
                f"{self.final_answer}\n\n[dim]Tool Usage: {tool_summary}[/dim]",
                title="[bold green]🎯 Final Answer[/bold green]",
                border_style="green"
            ))

        return Group(*elements)
```

**Step 2: Update __init__.py**

Add `SwimlaneVisualizer` to imports and `__all__`.

**Step 3: Verify swimlane visualizer**

Run: `python -c "from src.visualization import SwimlaneVisualizer; print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add src/visualization/
git commit -m "feat(viz): add swimlane visualizer for ReAct"
```

---

## Task 9: Create Step Visualizer (CoT)

**Files:**
- Create: `src/visualization/step_viz.py`

**Step 1: Create step visualizer**

```python
# src/visualization/step_viz.py
import re
from typing import Dict, List
from rich.console import RenderableType
from rich.panel import Panel
from rich.text import Text
from rich.console import Group

from .base import BaseVisualizer
from .models import StreamEvent, ChainStep

class StepVisualizer(BaseVisualizer):
    """Visualizer for Chain-of-Thought - numbered step panels with flow arrows."""

    STEP_ICONS = {
        "calculate": "🔢",
        "time": "⏱️",
        "divide": "➗",
        "analyze": "🔍",
        "conclude": "💡",
        "final": "✅",
        "default": "📌",
    }

    def __init__(self, query: str = "", **kwargs):
        super().__init__(**kwargs)
        self.query = query
        self.steps: Dict[int, ChainStep] = {}
        self.raw_content = ""
        self.final_answer = ""

    def _detect_icon(self, content: str) -> str:
        content_lower = content.lower()
        if any(w in content_lower for w in ["calculate", "compute", "multiply", "add", "subtract"]):
            return self.STEP_ICONS["calculate"]
        if any(w in content_lower for w in ["time", "hour", "minute", "second", "duration"]):
            return self.STEP_ICONS["time"]
        if any(w in content_lower for w in ["divide", "split", "ratio"]):
            return self.STEP_ICONS["divide"]
        if any(w in content_lower for w in ["analyze", "examine", "consider", "look"]):
            return self.STEP_ICONS["analyze"]
        if any(w in content_lower for w in ["therefore", "conclude", "result", "answer"]):
            return self.STEP_ICONS["conclude"]
        return self.STEP_ICONS["default"]

    def update(self, event: StreamEvent) -> None:
        if event.event_type == "chain_step" and isinstance(event.data, ChainStep):
            step = event.data
            step.icon = self._detect_icon(step.content)
            self.steps[step.step] = step
        elif event.event_type == "query" and isinstance(event.data, str):
            self.query = event.data
        elif event.event_type == "raw_content" and isinstance(event.data, str):
            self.raw_content = event.data
        elif event.event_type == "final_answer" and isinstance(event.data, str):
            self.final_answer = event.data

    def _parse_steps_from_raw(self) -> None:
        """Parse steps from raw content if not already structured."""
        if self.steps:
            return

        # Try to split by step markers
        patterns = [
            r"(?:Step\s+)?(\d+)[\.:\)]\s*(.+?)(?=(?:Step\s+)?\d+[\.:\)]|$)",
            r"(First|Second|Third|Next|Finally)[,:]?\s*(.+?)(?=(?:First|Second|Third|Next|Finally)[,:]|$)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, self.raw_content, re.IGNORECASE | re.DOTALL)
            if matches:
                for i, (_, content) in enumerate(matches, 1):
                    self.steps[i] = ChainStep(
                        step=i,
                        content=content.strip(),
                        icon=self._detect_icon(content)
                    )
                break

    def render(self) -> RenderableType:
        elements = []

        # Header
        elements.append(Panel(
            f"Query: {self.query}",
            title="[bold cyan]Chain-of-Thought Reasoning[/bold cyan]",
            border_style="cyan"
        ))

        # Try to parse if we have raw content but no steps
        if self.raw_content and not self.steps:
            self._parse_steps_from_raw()

        if not self.steps and not self.raw_content:
            elements.append(Text("Thinking step by step...", style="dim italic"))
            return Group(*elements)

        # If we have structured steps, render them
        if self.steps:
            total = len(self.steps)
            for step_num in sorted(self.steps.keys()):
                step = self.steps[step_num]

                content = step.content[:300] + "..." if len(step.content) > 300 else step.content

                elements.append(Panel(
                    f"{step.icon} {content}",
                    title=f"[bold]Step {step_num}[/bold]",
                    border_style="blue"
                ))

                # Arrow between steps
                if step_num < total:
                    elements.append(Text("                          │\n                          ▼", style="dim"))

            # Progress
            elements.append(Text(f"\nReasoning Progress: {'●───' * len(self.steps)}● {len(self.steps)}/{len(self.steps)}", style="dim"))
        else:
            # Fallback to raw content
            elements.append(Panel(self.raw_content, title="[bold]Reasoning[/bold]", border_style="blue"))

        # Final answer
        if self.final_answer:
            elements.append(Panel(
                self.final_answer,
                title="[bold green]🎯 Final Answer[/bold green]",
                border_style="green"
            ))

        return Group(*elements)
```

**Step 2: Update __init__.py**

Add `StepVisualizer` to imports and `__all__`.

**Step 3: Verify step visualizer**

Run: `python -c "from src.visualization import StepVisualizer; print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add src/visualization/
git commit -m "feat(viz): add step visualizer for chain-of-thought"
```

---

## Task 10: Create Visualizer Registry

**Files:**
- Modify: `src/visualization/__init__.py`

**Step 1: Add visualizer registry**

Update `src/visualization/__init__.py` to final form:

```python
# src/visualization/__init__.py
from .models import (
    TaskStatus,
    TreeNode,
    SubTask,
    VotingSample,
    ReflectionIteration,
    ReActStep,
    ChainStep,
    StreamEvent,
)
from .base import BaseVisualizer
from .tree_viz import TreeVisualizer
from .task_viz import TaskVisualizer
from .voting_viz import VotingVisualizer
from .diff_viz import DiffVisualizer
from .swimlane_viz import SwimlaneVisualizer
from .step_viz import StepVisualizer

VISUALIZER_MAP = {
    "tot": TreeVisualizer,
    "tree_of_thoughts": TreeVisualizer,
    "decomposed": TaskVisualizer,
    "least_to_most": TaskVisualizer,
    "ltm": TaskVisualizer,
    "recursive": TaskVisualizer,
    "rlm": TaskVisualizer,
    "consistency": VotingVisualizer,
    "self_consistency": VotingVisualizer,
    "reflection": DiffVisualizer,
    "self_reflection": DiffVisualizer,
    "react": SwimlaneVisualizer,
    "cot": StepVisualizer,
    "chain_of_thought": StepVisualizer,
    "standard": None,
}

def get_visualizer(strategy: str, **kwargs):
    """Get the appropriate visualizer for a strategy."""
    viz_class = VISUALIZER_MAP.get(strategy.lower())
    if viz_class:
        return viz_class(**kwargs)
    return None

__all__ = [
    "TaskStatus",
    "TreeNode",
    "SubTask",
    "VotingSample",
    "ReflectionIteration",
    "ReActStep",
    "ChainStep",
    "StreamEvent",
    "BaseVisualizer",
    "TreeVisualizer",
    "TaskVisualizer",
    "VotingVisualizer",
    "DiffVisualizer",
    "SwimlaneVisualizer",
    "StepVisualizer",
    "VISUALIZER_MAP",
    "get_visualizer",
]
```

**Step 2: Verify registry**

Run: `python -c "from src.visualization import get_visualizer, VISUALIZER_MAP; print(len(VISUALIZER_MAP), 'strategies mapped')"`
Expected: `14 strategies mapped`

**Step 3: Commit**

```bash
git add src/visualization/
git commit -m "feat(viz): add visualizer registry and get_visualizer helper"
```

---

## Task 11: Update Agent Defaults

**Files:**
- Modify: `src/agents/consistency.py`
- Modify: `src/agents/self_reflection.py`
- Modify: `src/agents/react.py`

**Step 1: Update ConsistencyAgent samples to k=5**

In `src/agents/consistency.py`, change line 8:
```python
def __init__(self, model="gemma3:270m", samples=5):
```

**Step 2: Update SelfReflectionAgent max_turns to 5**

In `src/agents/self_reflection.py`, change line 23:
```python
max_turns = 5
```

**Step 3: Update ReActAgent max_steps to 5**

In `src/agents/react.py`, change line 115:
```python
max_steps = 5
```

**Step 4: Verify changes**

Run: `grep -n "samples=5\|max_turns = 5\|max_steps = 5" src/agents/*.py`
Expected: Shows all three files with updated values

**Step 5: Commit**

```bash
git add src/agents/consistency.py src/agents/self_reflection.py src/agents/react.py
git commit -m "feat(agents): increase default iterations - k=5, max_turns=5, max_steps=5"
```

---

## Task 12: Refactor ToT Agent for Structured Events

**Files:**
- Modify: `src/agents/tot.py`

**Step 1: Add structured streaming to ToTAgent**

Replace the entire `src/agents/tot.py`:

```python
from src.agents.base import BaseAgent
from src.visualization.models import TreeNode, StreamEvent, TaskStatus
from termcolor import colored
import re

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
        """Legacy text streaming for backward compatibility."""
        for event in self.stream_structured(query):
            if event.event_type == "text":
                yield event.data
            elif event.event_type == "node":
                node = event.data
                score_str = f" (score: {node.score:.2f})" if node.score else ""
                best = " ★" if node.is_best else ""
                yield f"\n  Branch {node.id}{score_str}{best}: {node.content[:100]}...\n"
            elif event.event_type == "final":
                yield f"\n{event.data}"

    def stream_structured(self, query):
        """Structured event streaming for visualization."""
        yield StreamEvent(event_type="query", data=query)
        yield StreamEvent(event_type="text", data=f"Thinking via Tree of Thoughts (Depth={self.depth}, Width={self.width})...\n")

        current_thoughts = [("", None)]  # (thought_path, parent_id)
        node_counter = 0
        all_nodes = {}

        for step in range(self.depth):
            yield StreamEvent(event_type="text", data=f"\n[Step {step + 1}/{self.depth} - Exploring branches]\n")

            candidates = []

            # 1. Generate Candidates
            for thought_path, parent_id in current_thoughts:
                prompt = f"Problem: {query}\nCurrent reasoning path:\n{thought_path}\n\nProvide {self.width} distinct possible next steps or continuations to solve this problem. Label them Option 1, Option 2, etc."

                response = ""
                for chunk in self.client.generate(prompt, stream=False):
                    response += chunk

                options = [opt for opt in response.split("Option ") if opt.strip()]
                if not options:
                    options = [response]
                options = options[:self.width]

                for i, opt in enumerate(options):
                    node_counter += 1
                    node_id = f"{chr(65 + (node_counter - 1) // self.width)}{(node_counter - 1) % self.width + 1}" if step > 0 else chr(65 + i)
                    new_thought = thought_path + "\n" + opt.strip()
                    candidates.append((new_thought, node_id, parent_id, opt.strip()))

            # 2. Evaluate Candidates
            scored_candidates = []
            for thought_path, node_id, parent_id, content in candidates:
                eval_prompt = f"Problem: {query}\nProposed Reasoning Path:\n{thought_path}\n\nRate this reasoning path from 0.0 to 1.0 based on correctness and promise. Output ONLY the number."

                score_str = ""
                for chunk in self.client.generate(eval_prompt, stream=False):
                    score_str += chunk

                try:
                    match = re.search(r"Score:\s*(0\.\d+|1\.0|0|1)", score_str, re.IGNORECASE)
                    if not match:
                        match = re.search(r"\b(0\.\d+|1\.0|0|1)\b", score_str)
                    score = float(match.group(1)) if match else 0.1
                except:
                    score = 0.1

                node = TreeNode(
                    id=node_id,
                    depth=step + 1,
                    content=content,
                    score=score,
                    parent_id=parent_id
                )
                all_nodes[node_id] = node
                yield StreamEvent(event_type="node", data=node)

                scored_candidates.append((score, thought_path, node_id, content))

            # 3. Prune - keep top width
            scored_candidates.sort(key=lambda x: x[0], reverse=True)
            kept = scored_candidates[:self.width]
            pruned = scored_candidates[self.width:]

            # Mark pruned nodes
            for _, _, node_id, _ in pruned:
                if node_id in all_nodes:
                    all_nodes[node_id].is_pruned = True
                    yield StreamEvent(event_type="node", data=all_nodes[node_id], is_update=True)

            current_thoughts = [(path, nid) for _, path, nid, _ in kept]

        # Mark best path
        if current_thoughts:
            best_path, best_id = current_thoughts[0]
            if best_id in all_nodes:
                all_nodes[best_id].is_best = True
                yield StreamEvent(event_type="node", data=all_nodes[best_id], is_update=True)
        else:
            best_path = "No valid path found."

        yield StreamEvent(event_type="text", data="\n[Best Logic Trace selected. Generating Final Answer]\n")

        final_prompt = f"Problem: {query}\n\nReasoning Trace:\n{best_path}\n\nInstruction: Based on the reasoning above, provide a comprehensive and detailed final answer to the problem."
        system_msg = "You are a logic engine. You provide detailed, academic answers based on reasoning traces. Do not use conversational fillers like 'Okay' or 'Sure'."

        final_response = ""
        for chunk in self.client.generate(final_prompt, system=system_msg):
            final_response += chunk
            yield StreamEvent(event_type="text", data=chunk)

        yield StreamEvent(event_type="final", data=final_response)
```

**Step 2: Verify ToT agent works**

Run: `python -c "from src.agents.tot import ToTAgent; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add src/agents/tot.py
git commit -m "feat(tot): add structured event streaming for visualization"
```

---

## Task 13: Refactor Decomposed Agent for Structured Events

**Files:**
- Modify: `src/agents/decomposed.py`

**Step 1: Add structured streaming to DecomposedAgent**

Replace entire `src/agents/decomposed.py`:

```python
from src.agents.base import BaseAgent
from src.visualization.models import SubTask, StreamEvent, TaskStatus
from termcolor import colored

class DecomposedAgent(BaseAgent):
    def __init__(self, model="gemma3:270m"):
        super().__init__(model)
        self.name = "DecomposedAgent"
        self.color = "red"

    def run(self, query):
        response = ""
        for chunk in self.stream(query):
            response += chunk
        return response

    def stream(self, query):
        """Legacy text streaming for backward compatibility."""
        for event in self.stream_structured(query):
            if event.event_type == "text":
                yield event.data
            elif event.event_type == "task":
                task = event.data
                if task.status == TaskStatus.RUNNING:
                    yield f"\n**Solving sub-task:** `{task.description}`\nResult: "
                elif task.status == TaskStatus.COMPLETED and task.result:
                    yield task.result + "\n"

    def stream_structured(self, query):
        """Structured event streaming for visualization."""
        yield StreamEvent(event_type="query", data=query)
        yield StreamEvent(event_type="text", data=f"Processing query by decomposing: {query}\n")

        # 1. Decompose
        yield StreamEvent(event_type="text", data="\n**Decomposing the problem...**\n")
        decomposition_prompt = f"Break down the following complex problem into a numbered list of simple sub-tasks.\nProblem: {query}\nProvide only the list."

        sub_tasks_text = ""
        for chunk in self.client.generate(decomposition_prompt):
            sub_tasks_text += chunk

        yield StreamEvent(event_type="text", data=f"\n### Sub-tasks Plan:\n{sub_tasks_text}\n")

        # Parse sub-tasks
        lines = sub_tasks_text.split('\n')
        tasks = []
        task_id = 0
        for line in lines:
            line = line.strip()
            if not line:
                continue
            task_id += 1
            task = SubTask(id=task_id, description=line, status=TaskStatus.PENDING)
            tasks.append(task)
            yield StreamEvent(event_type="task", data=task)

        # 2. Execute Sub-tasks
        context = ""

        for task in tasks:
            # Mark as running
            task.status = TaskStatus.RUNNING
            yield StreamEvent(event_type="task", data=task, is_update=True)

            # Solve with context
            solve_prompt = f"Context so far:\n{context}\n\nCurrent Task: {task.description}\nSolve this task efficiently."

            task_solution = ""
            chunks_received = 0
            for chunk in self.client.generate(solve_prompt):
                task_solution += chunk
                chunks_received += 1
                # Update progress estimate
                task.progress = min(0.9, chunks_received * 0.1)
                task.result = task_solution
                yield StreamEvent(event_type="task", data=task, is_update=True)

            # Mark as completed
            task.status = TaskStatus.COMPLETED
            task.progress = 1.0
            task.result = task_solution
            yield StreamEvent(event_type="task", data=task, is_update=True)

            context += f"Task: {task.description}\nResult: {task_solution}\n"

        # 3. Synthesize
        yield StreamEvent(event_type="text", data="\n**Synthesizing final answer...**\n")
        synthesis_prompt = f"Original Query: {query}\n\nCompleted Sub-tasks results:\n{context}\n\nProvide the final comprehensive answer."

        yield StreamEvent(event_type="text", data="### Final Answer:\n")
        final_response = ""
        for chunk in self.client.generate(synthesis_prompt):
            final_response += chunk
            yield StreamEvent(event_type="text", data=chunk)

        yield StreamEvent(event_type="final", data=final_response)
```

**Step 2: Verify decomposed agent**

Run: `python -c "from src.agents.decomposed import DecomposedAgent; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add src/agents/decomposed.py
git commit -m "feat(decomposed): add structured event streaming for visualization"
```

---

## Task 14: Refactor Consistency Agent for Structured Events

**Files:**
- Modify: `src/agents/consistency.py`

**Step 1: Add structured streaming**

Replace entire `src/agents/consistency.py`:

```python
from src.agents.base import BaseAgent
from src.visualization.models import VotingSample, StreamEvent, TaskStatus
from termcolor import colored
from collections import Counter
import re

class ConsistencyAgent(BaseAgent):
    def __init__(self, model="gemma3:270m", samples=5):
        super().__init__(model)
        self.name = "ConsistencyAgent"
        self.color = "cyan"
        self.samples = samples

    def run(self, query):
        response = ""
        for chunk in self.stream(query):
            response += chunk
        return response

    def stream(self, query):
        """Legacy text streaming for backward compatibility."""
        for event in self.stream_structured(query):
            if event.event_type == "text":
                yield event.data
            elif event.event_type == "sample":
                sample = event.data
                if sample.status == TaskStatus.COMPLETED:
                    yield f"\n   -> *Extracted Answer: {sample.answer}*\n"

    def stream_structured(self, query):
        """Structured event streaming for visualization."""
        yield StreamEvent(event_type="query", data=query)
        yield StreamEvent(event_type="text", data=f"Processing query via Self-Consistency (k={self.samples}): {query}\n")

        samples = []

        for i in range(self.samples):
            sample = VotingSample(id=i + 1, status=TaskStatus.RUNNING)
            samples.append(sample)
            yield StreamEvent(event_type="sample", data=sample)

            yield StreamEvent(event_type="text", data=f"\n**[Path {i+1}/{self.samples}]**\n")

            prompt = f"Question: {query}\nThink step-by-step to answer this question. End your answer with 'Final Answer: <answer>'."

            trace_content = ""
            for chunk in self.client.generate(prompt, temperature=0.7, stream=True):
                trace_content += chunk
                sample.reasoning = trace_content
                yield StreamEvent(event_type="sample", data=sample, is_update=True)
                yield StreamEvent(event_type="text", data=chunk)

            # Extract Final Answer
            match = re.search(r"Final Answer:\s*(.*)", trace_content, re.IGNORECASE)
            final_ans = match.group(1).strip() if match else "Unknown"

            sample.answer = final_ans
            sample.status = TaskStatus.COMPLETED
            yield StreamEvent(event_type="sample", data=sample, is_update=True)

        # Majority Voting
        answers = [s.answer for s in samples]
        counter = Counter(answers)
        best_answer, count = counter.most_common(1)[0]

        # Mark winners
        for sample in samples:
            sample.votes = counter[sample.answer]
            sample.is_winner = sample.answer == best_answer
            yield StreamEvent(event_type="sample", data=sample, is_update=True)

        yield StreamEvent(event_type="voting_complete", data=True)

        yield StreamEvent(event_type="text", data="\n---\n")
        yield StreamEvent(event_type="text", data=f"**Majority Logic:** {best_answer} ({count}/{self.samples} votes)\n")
        yield StreamEvent(event_type="text", data="\n**Final Consolidated Answer:**\n")
        yield StreamEvent(event_type="text", data=best_answer)
        yield StreamEvent(event_type="text", data="\n")

        yield StreamEvent(event_type="final", data=best_answer)
```

**Step 2: Verify consistency agent**

Run: `python -c "from src.agents.consistency import ConsistencyAgent; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add src/agents/consistency.py
git commit -m "feat(consistency): add structured event streaming for visualization"
```

---

## Task 15: Refactor Self-Reflection Agent for Structured Events

**Files:**
- Modify: `src/agents/self_reflection.py`

**Step 1: Add structured streaming**

Replace entire `src/agents/self_reflection.py`:

```python
from src.agents.base import BaseAgent
from src.visualization.models import ReflectionIteration, StreamEvent
from termcolor import colored

class SelfReflectionAgent(BaseAgent):
    def __init__(self, model="gemma3:270m"):
        super().__init__(model)
        self.name = "SelfReflectionAgent"
        self.color = "green"

    def run(self, query):
        self.log_thought(f"Processing query with Self-Reflection: {query}")
        full_response = ""
        for chunk in self.stream(query):
            print(colored(chunk, self.color), end="", flush=True)
            full_response += chunk
        print()
        return full_response

    def stream(self, query):
        """Legacy text streaming for backward compatibility."""
        for event in self.stream_structured(query):
            if event.event_type == "text":
                yield event.data
            elif event.event_type == "iteration":
                iteration = event.data
                if iteration.is_correct:
                    yield colored("\n[Critique passed. Answer is correct.]\n", "green")

    def stream_structured(self, query):
        """Structured event streaming for visualization."""
        max_turns = 5
        current_answer = ""

        yield StreamEvent(event_type="query", data=query)

        # 1. Initial Attempt
        yield StreamEvent(event_type="text", data="[Drafting initial response...]\n")
        initial_prompt = f"Answer the following question: {query}"

        iteration = ReflectionIteration(iteration=1, draft="")
        yield StreamEvent(event_type="iteration", data=iteration)
        yield StreamEvent(event_type="phase", data="draft")

        yield StreamEvent(event_type="text", data="Initial Draft: ")
        for chunk in self.client.generate(initial_prompt):
            current_answer += chunk
            iteration.draft = current_answer
            yield StreamEvent(event_type="iteration", data=iteration, is_update=True)
            yield StreamEvent(event_type="text", data=chunk)
        yield StreamEvent(event_type="text", data="\n\n")

        # 2. Reflection Loop
        for turn in range(max_turns):
            yield StreamEvent(event_type="text", data=f"\n[Reflection Turn {turn+1}/{max_turns}]\n")

            # Create new iteration for turns > 0
            if turn > 0:
                iteration = ReflectionIteration(iteration=turn + 1, draft=current_answer)
                yield StreamEvent(event_type="iteration", data=iteration)

            # Critique
            yield StreamEvent(event_type="phase", data="critique")
            critique_prompt = f"Review the following answer to the question: '{query}'.\nAnswer: '{current_answer}'.\nIf the answer is correct and complete, output ONLY 'CORRECT'. Otherwise, list the errors."
            critique = ""
            yield StreamEvent(event_type="text", data="Critique: ")
            for chunk in self.client.generate(critique_prompt):
                critique += chunk
                iteration.critique = critique
                yield StreamEvent(event_type="iteration", data=iteration, is_update=True)
                yield StreamEvent(event_type="text", data=chunk)
            yield StreamEvent(event_type="text", data="\n")

            if "CORRECT" in critique.upper() and len(critique) < 20:
                iteration.is_correct = True
                yield StreamEvent(event_type="iteration", data=iteration, is_update=True)
                break

            # Improvement
            yield StreamEvent(event_type="phase", data="improvement")
            yield StreamEvent(event_type="text", data="Refining Answer...\n")
            improvement_prompt = f"Original Question: {query}\nCurrent Answer: {current_answer}\nCritique: {critique}\n\nProvide the corrected final answer."

            new_answer = ""
            for chunk in self.client.generate(improvement_prompt):
                new_answer += chunk
                iteration.improvement = new_answer
                yield StreamEvent(event_type="iteration", data=iteration, is_update=True)
                yield StreamEvent(event_type="text", data=chunk)
            yield StreamEvent(event_type="text", data="\n")
            current_answer = new_answer

        yield StreamEvent(event_type="text", data=f"\nFinal Result: {current_answer}\n")
        yield StreamEvent(event_type="final", data=current_answer)
```

**Step 2: Verify self-reflection agent**

Run: `python -c "from src.agents.self_reflection import SelfReflectionAgent; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add src/agents/self_reflection.py
git commit -m "feat(reflection): add structured event streaming for visualization"
```

---

## Task 16: Refactor ReAct Agent for Structured Events

**Files:**
- Modify: `src/agents/react.py`

**Step 1: Add structured streaming**

Add these imports at the top of `src/agents/react.py`:
```python
from src.visualization.models import ReActStep, StreamEvent, TaskStatus
```

Then add the `stream_structured` method after the existing `stream` method:

```python
    def stream_structured(self, query):
        """Structured event streaming for visualization."""
        yield StreamEvent(event_type="query", data=query)

        system_prompt = """You are a Reasoning and Acting agent.
Tools:
- web_search[query]: SEARCH THE WEB. Use this for ANY question about current events, people, companies, or news.
- calculate[expression]: Use for math.
- search[query]: Use ONLY for definitions.

Instructions:
1. Answer the Question.
2. Trigger a tool using 'Action: tool[input]'.
3. Wait for 'Observation:' (do not generate it).
"""
        messages = f"{system_prompt}\nQuestion: {query}\n"
        max_steps = 5

        for i in range(max_steps):
            step = ReActStep(step=i + 1, status=TaskStatus.RUNNING)
            yield StreamEvent(event_type="react_step", data=step)

            yield StreamEvent(event_type="text", data=f"\n--- Step {i+1} ---\nAgent: ")

            response_chunk = ""
            for chunk in self.client.generate(messages, stream=True, stop=["Observation:"]):
                yield StreamEvent(event_type="text", data=chunk)
                response_chunk += chunk

            # Parse thought (everything before Action:)
            thought_match = re.search(r"^(.*?)(?=Action:|$)", response_chunk, re.DOTALL)
            if thought_match:
                step.thought = thought_match.group(1).strip()

            # Check for Action
            match = re.search(r"Action:\s*(\w+)\s*\[(.*?)\]", response_chunk, re.IGNORECASE)

            if match:
                tool_name = match.group(1).lower()
                tool_input = match.group(2)

                step.action = tool_name
                step.action_input = tool_input
                yield StreamEvent(event_type="react_step", data=step, is_update=True)

                action_full_str = match.group(0)
                idx = response_chunk.find(action_full_str)
                valid_part = response_chunk[:idx + len(action_full_str)]
                messages = messages[:-len(response_chunk)] + valid_part

                yield StreamEvent(event_type="text", data=f"\nRunning {tool_name}...")
                observation = self.perform_tool_call(tool_name, tool_input)

                step.observation = observation
                step.status = TaskStatus.COMPLETED
                yield StreamEvent(event_type="react_step", data=step, is_update=True)

                obs_str = f"\nObservation: {observation}\n"
                yield StreamEvent(event_type="text", data=colored(obs_str, "blue"))
                messages += obs_str
                continue

            # Check for final answer
            if "Final Answer:" in response_chunk:
                final_match = re.search(r"Final Answer:\s*(.*)", response_chunk, re.DOTALL)
                if final_match:
                    final_answer = final_match.group(1).strip()
                    step.status = TaskStatus.COMPLETED
                    yield StreamEvent(event_type="react_step", data=step, is_update=True)
                    yield StreamEvent(event_type="final_answer", data=final_answer)
                return

            step.status = TaskStatus.COMPLETED
            yield StreamEvent(event_type="react_step", data=step, is_update=True)
```

**Step 2: Verify react agent**

Run: `python -c "from src.agents.react import ReActAgent; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add src/agents/react.py
git commit -m "feat(react): add structured event streaming for visualization"
```

---

## Task 17: Refactor CoT Agent for Structured Events

**Files:**
- Modify: `src/agents/cot.py`

**Step 1: Add structured streaming**

Replace entire `src/agents/cot.py`:

```python
from src.agents.base import BaseAgent
from src.visualization.models import ChainStep, StreamEvent
from termcolor import colored
import re

class CoTAgent(BaseAgent):
    def __init__(self, model="gemma3:270m"):
        super().__init__(model)
        self.name = "CoTAgent"
        self.color = "blue"

    def run(self, query):
        self.log_thought(f"Processing query with Chain-of-Thought: {query}")
        print(colored("Reasoning: ", self.color), end="", flush=True)
        full_response = ""
        for chunk in self.stream(query):
            print(colored(chunk, self.color), end="", flush=True)
            full_response += chunk
        print()
        return full_response

    def stream(self, query):
        """Legacy text streaming for backward compatibility."""
        for event in self.stream_structured(query):
            if event.event_type == "text":
                yield event.data

    def stream_structured(self, query):
        """Structured event streaming for visualization."""
        yield StreamEvent(event_type="query", data=query)

        prompt = f"Question: {query}\n\nInstruction: Think step-by-step to answer the question. Break down the reasoning process clearly. Number each step. Provide a detailed final answer."

        full_response = ""
        current_step_content = ""
        current_step_num = 0

        # Step detection patterns
        step_pattern = re.compile(r'^(?:Step\s+)?(\d+)[\.:\)]', re.MULTILINE)

        for chunk in self.client.generate(prompt):
            full_response += chunk
            current_step_content += chunk
            yield StreamEvent(event_type="text", data=chunk)
            yield StreamEvent(event_type="raw_content", data=full_response)

            # Check if we've completed a step
            lines = current_step_content.split('\n')
            for line in lines[:-1]:  # Don't process incomplete last line
                match = step_pattern.match(line.strip())
                if match and int(match.group(1)) > current_step_num:
                    # New step detected
                    if current_step_num > 0:
                        # Emit previous step
                        pass  # Step emission handled by visualizer parsing
                    current_step_num = int(match.group(1))

        # Parse final answer
        final_match = re.search(r'(?:Final Answer|Therefore|Thus|In conclusion)[:\s]*(.+?)$', full_response, re.IGNORECASE | re.DOTALL)
        if final_match:
            yield StreamEvent(event_type="final_answer", data=final_match.group(1).strip())

        yield StreamEvent(event_type="final", data=full_response)
```

**Step 2: Verify cot agent**

Run: `python -c "from src.agents.cot import CoTAgent; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add src/agents/cot.py
git commit -m "feat(cot): add structured event streaming for visualization"
```

---

## Task 18: Update CLI to Use Visualizers

**Files:**
- Modify: `agent_cli.py`

**Step 1: Add visualization imports and helper**

At the top of `agent_cli.py`, add:
```python
from src.visualization import get_visualizer, VISUALIZER_MAP
```

**Step 2: Create new run_agent_chat_viz function**

Add this function after the existing `run_agent_chat`:

```python
def run_agent_chat_viz(strategy):
    """Run agent chat with rich visualization."""
    print_header()
    console.print(f"[bold yellow]Chat Mode: {strategy.upper()} (Visualized)[/bold yellow]")
    console.print("Type 'exit' or '0' to return.")

    while True:
        query = Prompt.ask("\n[bold green]Query[/bold green]")
        if query.lower() in ['exit', 'quit', '0']:
            break

        full_model_name = f"{MODEL_NAME}+{strategy}"
        console.print(f"[dim]Using model: {full_model_name}[/dim]")

        # Get visualizer
        visualizer = get_visualizer(strategy, query=query)

        if visualizer:
            # Use structured streaming with visualizer
            from src.interceptor import AGENT_MAP
            agent_class = AGENT_MAP.get(strategy)
            if agent_class:
                agent = agent_class(model=MODEL_NAME)
                if hasattr(agent, 'stream_structured'):
                    visualizer.run(agent.stream_structured(query))
                    continue

        # Fallback to standard display
        full_response = ""
        with Live("", refresh_per_second=10, vertical_overflow="visible") as live:
            try:
                for chunk_dict in client.generate(model=full_model_name, prompt=query, stream=True):
                    chunk = chunk_dict.get("response", "")
                    full_response += chunk
                    live.update(Markdown(full_response))
            except Exception as e:
                console.print(f"[bold red]Error:[/bold red] {e}")
```

**Step 3: Update menu choices to use visualization**

In `main_menu()`, update the handler mappings to use `run_agent_chat_viz` instead of `run_agent_chat` for strategies with visualizers.

**Step 4: Verify CLI loads**

Run: `python -c "import agent_cli; print('OK')"`
Expected: `OK`

**Step 5: Commit**

```bash
git add agent_cli.py
git commit -m "feat(cli): integrate visualizers into agent chat mode"
```

---

## Task 19: Integration Test

**Step 1: Run manual test**

```bash
python agent_cli.py
# Select ToT, enter a test query, verify visualization appears
# Select Decomposed, verify task tree with progress bars
# etc.
```

**Step 2: Verify all imports work**

```bash
python -c "
from src.visualization import *
from src.agents.tot import ToTAgent
from src.agents.decomposed import DecomposedAgent
from src.agents.consistency import ConsistencyAgent
from src.agents.self_reflection import SelfReflectionAgent
from src.agents.react import ReActAgent
from src.agents.cot import CoTAgent
print('All imports OK')
"
```
Expected: `All imports OK`

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat: complete visualization overhaul implementation"
```

---

## Summary

This plan implements:
1. **6 visualizers** in `src/visualization/`
2. **Structured event models** via dataclasses
3. **Agent refactoring** for structured streaming
4. **Updated defaults** (k=5, max_turns=5, max_steps=5)
5. **CLI integration** with visualizer registry

Total: 19 tasks, ~45-60 commits
