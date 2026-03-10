# src/visualization/__init__.py
from .analogy_viz import AnalogyVisualizer
from .base import BaseVisualizer
from .debate_viz import DebateVisualizer
from .diff_viz import DiffVisualizer
from .models import (
    ChainStep,
    PipelineIteration,
    ReActStep,
    RefinementIteration,
    ReflectionIteration,
    StreamEvent,
    SubTask,
    TaskStatus,
    TreeNode,
    VotingSample,
)
from .pipeline_viz import PipelineVisualizer
from .socratic_viz import SocraticVisualizer
from .step_viz import StepVisualizer
from .swimlane_viz import SwimlaneVisualizer
from .task_viz import TaskVisualizer
from .tree_viz import TreeVisualizer
from .voting_viz import VotingVisualizer

VISUALIZER_MAP = {
    "tot": TreeVisualizer,
    "tree_of_thoughts": TreeVisualizer,
    "decomposed": TaskVisualizer,
    "least_to_most": TaskVisualizer,
    "ltm": TaskVisualizer,
    # recursive/rlm uses text mode - no structured streaming
    "consistency": VotingVisualizer,
    "self_consistency": VotingVisualizer,
    "reflection": DiffVisualizer,
    "self_reflection": DiffVisualizer,
    "refinement": DiffVisualizer,
    "refinement_loop": DiffVisualizer,
    "iterative_refinement": DiffVisualizer,
    "complex_refinement": PipelineVisualizer,
    "pipeline": PipelineVisualizer,
    "react": SwimlaneVisualizer,
    "cot": StepVisualizer,
    "chain_of_thought": StepVisualizer,
    "debate": DebateVisualizer,
    "adversarial_debate": DebateVisualizer,
    "analogy": AnalogyVisualizer,
    "analogical": AnalogyVisualizer,
    "analogical_reasoning": AnalogyVisualizer,
    "socratic": SocraticVisualizer,
    "socratic_method": SocraticVisualizer,
    # MCTS reuses TreeVisualizer
    "mcts": TreeVisualizer,
    "monte_carlo": TreeVisualizer,
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
    "RefinementIteration",
    "PipelineIteration",
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
    "PipelineVisualizer",
    "DebateVisualizer",
    "AnalogyVisualizer",
    "SocraticVisualizer",
    "VISUALIZER_MAP",
    "get_visualizer",
]
