"""
Agent Reasoning: Transform LLMs into robust problem-solving agents.

Usage:
    from agent_reasoning import ReasoningInterceptor
    from agent_reasoning.agents import CoTAgent, ToTAgent
    from agent_reasoning.ensemble import ReasoningEnsemble
"""

from agent_reasoning.interceptor import ReasoningInterceptor, AGENT_MAP
from agent_reasoning.client import OllamaClient
from agent_reasoning.ensemble import ReasoningEnsemble

__version__ = "1.0.1"
__all__ = ["ReasoningInterceptor", "ReasoningEnsemble", "OllamaClient", "AGENT_MAP"]
