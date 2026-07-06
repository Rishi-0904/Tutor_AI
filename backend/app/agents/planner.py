"""
planner.py
----------
Execution Planner — deterministic scheduling of agents.

Separates intent (Orchestrator) from execution (Planner).
Determines:
  - Which agents can run in parallel
  - Which agents must run sequentially (dependencies)
  - Post-processing steps (memory, composer)

Future-proof: adding OCR/Image/Simulation agents = one config change.
"""

from __future__ import annotations

from typing import Any, Dict

from langchain_core.runnables import RunnableConfig
from app.agents.context import AgentContext, ExecutionPlan


# ─────────────────────────────────────────────────────────────
# DEPENDENCY CONFIGURATION
# ─────────────────────────────────────────────────────────────

# Agents that can run concurrently (no dependencies on each other)
PARALLEL_AGENTS = {"research", "visual"}

# Agents that depend on parallel results (must run AFTER parallel phase)
DEPENDS_ON_PARALLEL = {"tutor"}

# Standalone agents (no dependencies, run alone)
STANDALONE_AGENTS = {"quiz", "roadmap", "teach_back"}


# ─────────────────────────────────────────────────────────────
# PLANNER NODE
# ─────────────────────────────────────────────────────────────

async def planner_node(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    """
    LangGraph node: Execution Planner (deterministic).

    Reads the orchestrator's intent list and creates an ExecutionPlan
    specifying which agents run in parallel vs. sequentially.

    Rules:
      - research and visual can run in parallel (independent data fetching)
      - tutor depends on research/visual results (runs after parallel phase)
      - quiz, roadmap, teach_back are standalone (run directly, no parallel)
      - memory and composer always run last (post-processing)
    """
    ctx = AgentContext(**state["context"])
    intent = ctx.intent

    parallel = []
    sequential = []

    for agent_name in intent:
        if agent_name in PARALLEL_AGENTS:
            parallel.append(agent_name)
        elif agent_name in DEPENDS_ON_PARALLEL:
            sequential.append(agent_name)
        elif agent_name in STANDALONE_AGENTS:
            sequential.append(agent_name)
        else:
            # Unknown agent — add to sequential as fallback
            sequential.append(agent_name)

    # If there are parallel agents but no tutor, ensure tutor runs after
    # parallel phase when research/visual produce context for it
    if parallel and "tutor" not in sequential:
        # Only add tutor if it was in the original intent
        pass

    # If tutor is in sequential and there are parallel agents,
    # tutor should come AFTER them (it's already in sequential which runs after parallel)

    plan = ExecutionPlan(
        parallel=parallel,
        sequential=sequential,
        post_processing=["memory", "composer"],
    )

    ctx.execution_plan = plan
    print(
        f"[Planner] Plan: parallel={plan.parallel}, "
        f"sequential={plan.sequential}, "
        f"post={plan.post_processing}"
    )

    return {"context": ctx.model_dump()}
