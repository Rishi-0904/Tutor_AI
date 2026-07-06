"""
registry.py
------------
Agent Registry for TutorAI.

Adding a new agent = one line:
    AgentRegistry.register("ocr", ocr_node)

No if/elif chains. Fully extensible.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional


class AgentRegistry:
    """
    Singleton registry mapping agent names to their async node functions.

    Usage:
        AgentRegistry.register("tutor", tutor_node)
        agent_fn = AgentRegistry.get("tutor")
        result = await agent_fn(state, config)
    """

    _agents: Dict[str, Callable] = {}

    @classmethod
    def register(cls, name: str, agent_fn: Callable) -> None:
        """Register an agent node function by name."""
        cls._agents[name] = agent_fn
        print(f"[AgentRegistry] Registered agent: {name}")

    @classmethod
    def get(cls, name: str) -> Callable:
        """Retrieve an agent node function by name. Raises if not found."""
        if name not in cls._agents:
            raise ValueError(
                f"Agent '{name}' is not registered. "
                f"Available: {list(cls._agents.keys())}"
            )
        return cls._agents[name]

    @classmethod
    def has(cls, name: str) -> bool:
        """Check whether an agent is registered."""
        return name in cls._agents

    @classmethod
    def list_agents(cls) -> List[str]:
        """Return names of all registered agents."""
        return list(cls._agents.keys())

    @classmethod
    def clear(cls) -> None:
        """Remove all registrations (useful for testing)."""
        cls._agents.clear()
