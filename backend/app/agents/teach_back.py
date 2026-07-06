"""
teach_back.py
-------------
Teach-Back Node — active recall assessment wrapper (deterministic).

Extracts concept from recent conversation history, evaluates student explanation
using existing service, and records scorecard details.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from google import genai as google_genai

from app.core.config import settings
from app.agents.context import AgentContext, TeachBackResult
from app.agents.prompts import CONCEPT_EXTRACTION_PROMPT
from app.services.teach_back_service import evaluate_student_explanation


async def _extract_concept_from_history(messages: List[BaseMessage]) -> str:
    """Helper to extract the active scientific/math/chem concept from history."""
    api_key = settings.gemini_api_key
    if not api_key or len(messages) < 2:
        return "General Concept"
        
    try:
        # Compile previous turns
        history_text = "\n".join(f"{type(m).__name__}: {m.content}" for m in messages[-4:-1])
        client = google_genai.Client(api_key=api_key)
        
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model="gemini-2.5-flash",
                contents=CONCEPT_EXTRACTION_PROMPT.format(history_text=history_text)
            )
        )
        if response and response.text:
            return response.text.strip()
    except Exception as e:
        print(f"[TeachBack] Error extracting concept: {e}")
        
    return "General Concept"


def _has_real_misconceptions(eval_result: Dict[str, Any]) -> bool:
    """Check if the evaluation output has actual flagged misconceptions."""
    misconceptions = eval_result.get("misconceptions", [])
    if not misconceptions:
        return False
        
    ignore_phrases = ["none", "none detected", "none detected!", "no misconceptions", "no misconceptions detected"]
    filtered = [m for m in misconceptions if m.strip().lower() not in ignore_phrases]
    return len(filtered) > 0


async def teach_back_node(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    """
    LangGraph node: Teach-Back active recall.

    Runs concept extraction and evaluates the user's message using the existing
    evaluate_student_explanation service.
    """
    ctx = AgentContext(**state["context"])
    messages = state["messages"]
    explanation = ctx.user_query

    # 1. Extract concept from history (RAG-like prompt call)
    concept = await _extract_concept_from_history(messages)
    print(f"[TeachBack] Active concept under discussion: '{concept}'")

    # 2. Evaluate student description
    loop = asyncio.get_running_loop()
    eval_res = await loop.run_in_executor(
        None,
        lambda: evaluate_student_explanation(concept, explanation)
    )
    eval_res["concept"] = concept

    # 3. Write results to shared context
    ctx.teach_back = TeachBackResult(
        score=eval_res.get("score", 50),
        coverage=eval_res.get("coverage", []),
        missing_concepts=eval_res.get("missing_concepts", []),
        misconceptions=eval_res.get("misconceptions", []),
        confidence=eval_res.get("confidence", "Medium"),
        feedback=eval_res.get("feedback", ""),
        concept=concept
    )

    # 4. Set memory/score flags
    if eval_res.get("score", 100) < 70 or _has_real_misconceptions(eval_res):
        ctx.is_correct = False
    else:
        ctx.is_correct = True
        
    # We flag mastery updates to be executed in the memory node
    ctx.mastery_changed = True
    ctx.mastery_updates.append({
        "topic": concept,
        "score": eval_res.get("score", 50)
    })

    print(f"[TeachBack] Evaluation scorecard written. Score: {eval_res.get('score')}")
    return {"context": ctx.model_dump()}
