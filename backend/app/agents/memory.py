"""
memory.py
---------
Memory Node — handles learning persistence (deterministic).

Saves chat history, conditionally updates weakness snapshots and mastery,
and creates conversation summaries when the message count grows.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from google import genai as google_genai

from app.core.config import settings
from app.core.supabase_client import supabase
from app.agents.context import AgentContext
from app.agents.prompts import CONVERSATION_SUMMARY_PROMPT
from app.services.history_service import save_assistant_message
from app.services.weakness_service import create_weakness_snapshot
from app.services.mcp_service import mcp_service


async def _generate_and_cache_summary(conversation_id: str, messages: List[BaseMessage]) -> None:
    """Amortized check: updates the conversation summary when thread grows."""
    api_key = settings.gemini_api_key
    if not api_key:
        return

    print(f"[MemoryNode] Generating summary update for conversation {conversation_id}...")
    try:
        # Compile last 10 messages
        history_text = "\n".join(f"{type(m).__name__}: {m.content}" for m in messages[-10:])
        client = google_genai.Client(api_key=api_key)
        
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model="gemini-2.5-flash",
                contents=CONVERSATION_SUMMARY_PROMPT.format(history_text=history_text)
            )
        )
        if response and response.text:
            summary = response.text.strip()
            print(f"[MemoryNode] Summary update: {summary}")
            
            # Cache in Redis
            from app.services.redis_service import cache
            cache.set(f"summary:{conversation_id}", summary, expire_seconds=86400)
            
            # Update title in database
            await loop.run_in_executor(
                None,
                lambda: supabase.table('conversations').update({
                    'title': summary[:100]
                }).eq('id', conversation_id).execute()
            )
    except Exception as e:
        print(f"[MemoryNode] Summary update failed: {e}")


async def memory_node(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    """
    LangGraph node: Memory Service.

    1. Always saves the final composed assistant message to Supabase.
    2. Conditionally updates weakness snapshots and mastery scores ONLY when state changes.
    3. Triggers conversation summary updates asynchronously.
    """
    ctx = AgentContext(**state["context"])
    messages = state["messages"]

    # Use the composed final response if available; fallback to raw tutor answer
    final_content = ctx.tutor_answer
    if "composed_response" in ctx.metadata:
        final_content = ctx.metadata["composed_response"]

    print(f"[MemoryNode] Saving message to database for user {ctx.user_id}")

    loop = asyncio.get_running_loop()

    # 1. ALWAYS: Save message to history
    await loop.run_in_executor(
        None,
        lambda: save_assistant_message(
            conversation_id=ctx.conversation_id,
            user_id=ctx.user_id,
            content=final_content,
            topic_tags=ctx.topic_tags,
            is_correct=ctx.is_correct
        )
    )

    # 2. CONDITIONAL: Update weakness snapshot only if learning state changed
    if ctx.mastery_changed:
        print(f"[MemoryNode] Learning state changed. Updating weakness snapshot.")
        await loop.run_in_executor(
            None,
            lambda: create_weakness_snapshot(ctx.user_id, ctx.subject)
        )

        # 3. CONDITIONAL: Update mastery scores via MCP client wrappers
        for update in ctx.mastery_updates:
            topic = update.get("topic")
            score = update.get("score", 50)
            if topic:
                print(f"[MemoryNode] Updating mastery score for topic '{topic}' to {score}%")
                await mcp_service.update_mastery_score(ctx.user_id, topic, score)

    # 4. CONDITIONAL: Update conversation summary periodically
    if len(messages) >= 8:
        # Run in background task to avoid blocking response pipeline
        asyncio.create_task(_generate_and_cache_summary(ctx.conversation_id, messages))

    return {"context": ctx.model_dump()}
