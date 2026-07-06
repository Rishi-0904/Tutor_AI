"""
orchestrator.py
---------------
Orchestrator Agent — LLM-powered intent classification.

Replaces the keyword-based router_node. Makes a single Gemini Flash call
with structured JSON output to determine which specialist agents are needed.

Does NOT answer questions. Does NOT schedule execution (that's the Planner).
Focus: intent only.
"""

from __future__ import annotations

import json
import asyncio
from typing import Any, Dict

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from app.core.config import settings
from app.agents.context import AgentContext
from app.agents.prompts import ORCHESTRATOR_PROMPT


# ─────────────────────────────────────────────────────────────
# DETERMINISTIC PRE-CHECKS (zero LLM cost)
# ─────────────────────────────────────────────────────────────

_TEACH_BACK_INVITATION_MARKER = "Would you like to explain this concept back to me"

_DECLINE_PHRASES = [
    "no", "no thanks", "nope", "not now", "skip",
    "don't want to", "explain more", "next topic", "sorry",
]


def _check_teach_back_response(messages) -> bool:
    """
    Fast deterministic check: is the user responding to a teach-back invitation?
    Returns True if we should route directly to teach_back (skipping LLM call).
    """
    # Find the last AI message
    last_ai_content = None
    for msg in reversed(messages[:-1]):
        if isinstance(msg, AIMessage):
            last_ai_content = msg.content
            break

    if not last_ai_content:
        return False

    # Check if last AI message contained the teach-back invitation
    if _TEACH_BACK_INVITATION_MARKER not in last_ai_content:
        return False

    # Check if user is declining
    user_msg = messages[-1].content.strip().lower()
    is_refusal = any(user_msg.startswith(d) for d in _DECLINE_PHRASES)
    is_short_question = user_msg.endswith("?") and len(user_msg.split()) < 6

    # If not declining and not a short question → treat as teach-back attempt
    return not is_refusal and not is_short_question


# ─────────────────────────────────────────────────────────────
# ORCHESTRATOR NODE
# ─────────────────────────────────────────────────────────────

async def orchestrator_node(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    """
    LangGraph node: Orchestrator Agent.

    1. Fast deterministic pre-check for teach-back responses (0 LLM cost).
    2. Single Gemini Flash call → structured JSON with agent selection.
    3. Writes intent + reasoning to AgentContext.
    """
    ctx = AgentContext(**state["context"])
    messages = state["messages"]

    # ── Deterministic pre-check: teach-back response ──
    if _check_teach_back_response(messages):
        print("[Orchestrator] Deterministic pre-check: teach-back response detected")
        ctx.intent = ["teach_back"]
        ctx.orchestrator_reasoning = "User is responding to teach-back invitation (deterministic detection)"
        return {"context": ctx.model_dump()}

    # ── LLM-based intent classification ──
    api_key = settings.gemini_api_key
    if not api_key:
        # Fallback: default to tutor
        print("[Orchestrator] No API key — defaulting to tutor")
        ctx.intent = ["tutor"]
        ctx.orchestrator_reasoning = "No API key available, defaulting to tutor"
        return {"context": ctx.model_dump()}

    user_message = messages[-1].content
    print(f"[Orchestrator] Classifying intent for: '{user_message[:80]}...'")

    try:
        from app.services.llm_provider import get_llm_provider
        provider = get_llm_provider()
        
        # Build standard messages log format
        chat_messages = [
            {"role": "system", "content": ORCHESTRATOR_PROMPT},
            {"role": "user", "content": f"Student message: {user_message}"}
        ]

        response = await provider.complete(
            model=settings.orchestrator_model,
            messages=chat_messages,
            json_mode=True
        )

        text_out = response.get("text") or ""
        if text_out:
            result = json.loads(text_out.strip())
            agents = result.get("agents", ["tutor"])
            reasoning = result.get("reasoning", "")

            # Validate agent names
            valid_agents = {"tutor", "research", "visual", "quiz", "roadmap", "teach_back"}
            agents = [a for a in agents if a in valid_agents]
            if not agents:
                agents = ["tutor"]

            ctx.intent = agents
            ctx.orchestrator_reasoning = reasoning
            print(f"[Orchestrator] Intent: {agents} | Reasoning: {reasoning}")
        else:
            ctx.intent = ["tutor"]
            ctx.orchestrator_reasoning = "Empty LLM response, defaulting to tutor"

    except Exception as e:
        print(f"[Orchestrator] Error: {e} — defaulting to tutor")
        ctx.intent = ["tutor"]
        ctx.orchestrator_reasoning = f"Error during classification: {e}"

    return {"context": ctx.model_dump()}
