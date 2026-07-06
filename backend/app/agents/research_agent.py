"""
research_agent.py
-----------------
Research Agent — searches immediately, no double-reasoning.

The Orchestrator already decided research is needed.
This agent does NOT ask "should I search?" — it searches. Period.

Uses Google Search Grounding + YouTube search tools in parallel.
"""

from __future__ import annotations

import json
import asyncio
from typing import Any, Dict

from langchain_core.runnables import RunnableConfig
from app.core.config import settings
from app.agents.context import AgentContext, ResearchResult
from app.agents.prompts import RESEARCH_PROMPT
from app.agents.tools import ToolRegistry


# Tools the Research Agent can invoke
RESEARCH_TOOL_NAMES = ["google_search", "youtube_search"]


async def research_node(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    """
    LangGraph node: Research Agent.

    Searches immediately using google_search and youtube_search tools.
    No "should I search?" reasoning — the Orchestrator already decided.

    Uses Gemini with tools to search and summarize findings.
    """
    ctx = AgentContext(**state["context"])
    query = ctx.user_query

    print(f"[ResearchAgent] Searching for: '{query[:80]}...'")

    try:
        from app.services.llm_provider import get_llm_provider
        provider = get_llm_provider()

        openai_tools = ToolRegistry.get_openai_tools(RESEARCH_TOOL_NAMES)
        chat_messages = [
            {"role": "system", "content": RESEARCH_PROMPT},
            {"role": "user", "content": f"Search for information about: {query}"}
        ]

        response = await provider.complete(
            model=settings.research_model,
            messages=chat_messages,
            tools=openai_tools
        )

        tool_calls = response.get("tool_calls") or []
        web_summary = response.get("text") or ""
        youtube_links = ""
        citations = []

        if tool_calls:
            # Execute tools in parallel
            tasks = []
            for tc in tool_calls:
                name = tc["function"]["name"]
                args = json.loads(tc["function"]["arguments"])
                tool = ToolRegistry.get(name)
                tasks.append((name, tc["id"], tool.aexecute(**args)))

            results = await asyncio.gather(*[t[2] for t in tasks], return_exceptions=True)

            for (name, _, _), result in zip(tasks, results):
                if isinstance(result, Exception):
                    print(f"[ResearchAgent] Tool {name} error: {result}")
                    continue
                if name == "google_search":
                    web_summary = str(result)
                elif name == "youtube_search":
                    youtube_links = str(result)

            # Send tool results back to LLM for a summary
            fn_responses = []
            for (name, call_id, _), result in zip(tasks, results):
                if not isinstance(result, Exception):
                    fn_responses.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "name": name,
                        "content": str(result)[:2000]
                    })

            if fn_responses:
                # Add assistant message with tool calls structure
                assistant_tc = []
                for tc in tool_calls:
                    assistant_tc.append({
                        "id": tc["id"],
                        "type": "function",
                        "function": tc["function"]
                    })
                
                summary_messages = [
                    {"role": "system", "content": RESEARCH_PROMPT},
                    {"role": "user", "content": f"Search for information about: {query}"},
                    {"role": "assistant", "content": None, "tool_calls": assistant_tc},
                ] + fn_responses

                summary_response = await provider.complete(
                    model=settings.research_model,
                    messages=summary_messages
                )
                web_summary = summary_response.get("text") or ""

        research_res = ResearchResult(
            web_summary=web_summary,
            citations=citations,
            youtube_links=youtube_links,
        )
        print(f"[ResearchAgent] Complete. Summary length: {len(web_summary)}")
        return {"research_output": research_res.model_dump()}

    except Exception as e:
        print(f"[ResearchAgent] Error: {e}")
        return await _direct_search_fallback(query)


async def _direct_search_fallback(query: str) -> Dict[str, Any]:
    """Fallback: call search tools directly without LLM reasoning."""
    try:
        google_tool = ToolRegistry.get("google_search")
        youtube_tool = ToolRegistry.get("youtube_search")

        web_result, yt_result = await asyncio.gather(
            google_tool.aexecute(query=query),
            youtube_tool.aexecute(query=query),
            return_exceptions=True,
        )

        research_res = ResearchResult(
            web_summary=str(web_result) if not isinstance(web_result, Exception) else "",
            youtube_links=str(yt_result) if not isinstance(yt_result, Exception) else "",
        )
    except Exception as e:
        print(f"[ResearchAgent] Fallback error: {e}")
        research_res = ResearchResult(web_summary=f"Search unavailable: {e}")

    return {"research_output": research_res.model_dump()}
