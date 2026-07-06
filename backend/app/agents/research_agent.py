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
from google import genai as google_genai
from google.genai import types

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

    api_key = settings.gemini_api_key
    if not api_key:
        # Direct fallback: call tools without LLM reasoning
        return await _direct_search_fallback(ctx, query)

    client = google_genai.Client(api_key=api_key)
    research_tools = ToolRegistry.get_gemini_tools(RESEARCH_TOOL_NAMES)

    loop = asyncio.get_running_loop()

    try:
        # Single Gemini call with search tools — agent searches immediately
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"Search for information about: {query}",
                config=types.GenerateContentConfig(
                    system_instruction=RESEARCH_PROMPT,
                    tools=[research_tools],
                ),
            ),
        )

        # Execute any tool calls
        candidate = response.candidates[0]
        function_calls = [p.function_call for p in candidate.content.parts if p.function_call]

        web_summary = ""
        youtube_links = ""
        citations = []

        if function_calls:
            # Execute tools in parallel
            tasks = []
            for fc in function_calls:
                tool = ToolRegistry.get(fc.name)
                tasks.append((fc.name, tool.aexecute(**dict(fc.args))))

            results = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)

            for (name, _), result in zip(tasks, results):
                if isinstance(result, Exception):
                    print(f"[ResearchAgent] Tool {name} error: {result}")
                    continue
                if name == "google_search":
                    web_summary = str(result)
                elif name == "youtube_search":
                    youtube_links = str(result)

            # Send tool results back to Gemini for a summary
            fn_response_parts = []
            for (name, _), result in zip(tasks, results):
                if not isinstance(result, Exception):
                    fn_response_parts.append(
                        types.Part.from_function_response(
                            name=name,
                            response={"result": str(result)[:2000]},
                        )
                    )

            if fn_response_parts:
                summary_response = await loop.run_in_executor(
                    None,
                    lambda: client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=[
                            types.Content(role="user", parts=[
                                types.Part.from_text(f"Search for information about: {query}")
                            ]),
                            candidate.content,
                            types.Content(role="user", parts=fn_response_parts),
                        ],
                        config=types.GenerateContentConfig(
                            system_instruction=RESEARCH_PROMPT,
                        ),
                    ),
                )
                if summary_response and summary_response.text:
                    web_summary = summary_response.text
        else:
            # Gemini answered directly (possibly via built-in knowledge)
            web_summary = ""
            for part in candidate.content.parts:
                if part.text:
                    web_summary += part.text

        ctx.research = ResearchResult(
            web_summary=web_summary,
            citations=citations,
            youtube_links=youtube_links,
        )
        print(f"[ResearchAgent] Complete. Summary length: {len(web_summary)}")

    except Exception as e:
        print(f"[ResearchAgent] Error: {e}")
        return await _direct_search_fallback(ctx, query)

    return {"context": ctx.model_dump()}


async def _direct_search_fallback(ctx: AgentContext, query: str) -> Dict[str, Any]:
    """Fallback: call search tools directly without LLM reasoning."""
    try:
        google_tool = ToolRegistry.get("google_search")
        youtube_tool = ToolRegistry.get("youtube_search")

        web_result, yt_result = await asyncio.gather(
            google_tool.aexecute(query=query),
            youtube_tool.aexecute(query=query),
            return_exceptions=True,
        )

        ctx.research = ResearchResult(
            web_summary=str(web_result) if not isinstance(web_result, Exception) else "",
            youtube_links=str(yt_result) if not isinstance(yt_result, Exception) else "",
        )
    except Exception as e:
        print(f"[ResearchAgent] Fallback error: {e}")
        ctx.research = ResearchResult(web_summary=f"Search unavailable: {e}")

    return {"context": ctx.model_dump()}
