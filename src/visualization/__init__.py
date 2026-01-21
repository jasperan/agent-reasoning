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
