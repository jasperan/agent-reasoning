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
