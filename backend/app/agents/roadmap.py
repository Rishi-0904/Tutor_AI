"""
roadmap.py
----------
Roadmap Node — learning path lookup wrapper (deterministic).

Invokes the existing roadmap_service to fetch or generate chapter dependencies.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict

from langchain_core.runnables import RunnableConfig
from app.agents.context import AgentContext, RoadmapResult
from app.services.roadmap_service import get_or_create_roadmap


async def roadmap_node(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    """
    LangGraph node: Roadmap.

    Queries the existing get_or_create_roadmap service dynamically.
    No LLM calls.
    """
    ctx = AgentContext(**state["context"])
    user_id = ctx.user_id
    subject = ctx.subject

    print(f"[RoadmapNode] Sourcing chapter roadmap for user {user_id} on {subject}")

    loop = asyncio.get_running_loop()
    try:
        steps = await loop.run_in_executor(
            None,
            lambda: get_or_create_roadmap(user_id, subject)
        )
        ctx.roadmap = RoadmapResult(steps=steps)
    except Exception as e:
        print(f"[RoadmapNode] Failed to load roadmap: {e}")
        ctx.roadmap = RoadmapResult(steps=[])

    return {"context": ctx.model_dump()}
