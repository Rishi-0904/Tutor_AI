"""
critic.py
---------
Critic Agent — evaluates response quality and handles loops (LLM).

Reviews the generated explanation from the Tutor Agent against the student's question
and research context to detect missing parts or inaccuracies.

Includes cycle-breaker protection to avoid infinite loops.
"""

from __future__ import annotations

import json
import asyncio
from typing import Any, Dict

from langchain_core.runnables import RunnableConfig
from app.core.config import settings
from app.agents.context import AgentContext, CriticFeedback
from app.agents.prompts import CRITIC_PROMPT


async def critic_node(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    """
    LangGraph node: Critic Agent.

    Evaluates the Tutor's output. If missing elements are found, triggers loop-backs
    to Research or Tutor. Protects against infinite cycles with a loop counter limit.
    """
    ctx = AgentContext(**state["context"])
    tutor_answer = ctx.tutor_answer
    user_query = ctx.user_query

    # 1. Loop-breaker check
    loops = ctx.metadata.get("critic_loops", 0)
    if loops >= 1:
        print(f"[Critic] Max cycles reached ({loops}). Auto-approving response.")
        ctx.critic_feedback = CriticFeedback(
            approved=True,
            feedback="Auto-approved due to safety loop-breaker protection.",
            action="approve",
            missing_elements=[]
        )
        return {"context": ctx.model_dump()}

    print(f"[Critic] Evaluating tutor response (Cycle {loops + 1})...")

    api_key = settings.gemini_api_key
    if not api_key:
        # Fallback: approve immediately
        ctx.critic_feedback = CriticFeedback(approved=True, action="approve")
        return {"context": ctx.model_dump()}

    # Compile context information for evaluation
    research_summary = ctx.research.web_summary if ctx.research else "None"
    
    evaluation_prompt = f"""
Student Question: {user_query}
Research Information Available: {research_summary}
Tutor Generated Explanation: {tutor_answer}
"""

    try:
        from app.services.llm_provider import get_llm_provider
        provider = get_llm_provider()

        chat_messages = [
            {"role": "system", "content": CRITIC_PROMPT},
            {"role": "user", "content": evaluation_prompt}
        ]

        response = await provider.complete(
            model=settings.critic_model,
            messages=chat_messages,
            json_mode=True
        )

        text_out = response.get("text") or ""
        if text_out:
            result = json.loads(text_out.strip())
            approved = result.get("approved", True)
            feedback = result.get("feedback", "")
            action = result.get("action", "approve")
            missing = result.get("missing_elements", [])

            # If rejected, increment loop counter
            if not approved and action in ("research", "revise"):
                ctx.metadata["critic_loops"] = loops + 1
                # If research is requested, append the new missing items to search query
                if missing:
                    ctx.user_query = f"{user_query} (Focus on: {', '.join(missing)})"

            ctx.critic_feedback = CriticFeedback(
                approved=approved,
                feedback=feedback,
                action=action,
                missing_elements=missing
            )
            print(f"[Critic] Result: Approved={approved} | Action={action} | Feedback='{feedback[:80]}...'")
        else:
            ctx.critic_feedback = CriticFeedback(approved=True, action="approve")

    except Exception as e:
        print(f"[Critic] Error: {e}. Default approving.")
        ctx.critic_feedback = CriticFeedback(approved=True, action="approve")

    return {"context": ctx.model_dump()}
