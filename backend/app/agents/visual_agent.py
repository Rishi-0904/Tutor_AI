"""
visual_agent.py
---------------
Visual Agent — visualization specialist.

The Orchestrator already decided visualization is needed.
This agent does NOT ask "should I draw?" — it only decides the type of
visualization (flowchart, function plot, DP table) and invokes the tools.
"""

from __future__ import annotations

import json
import asyncio
from typing import Any, Dict

from langchain_core.runnables import RunnableConfig
from app.core.config import settings
from app.agents.context import AgentContext, VisualizationResult
from app.agents.prompts import VISUAL_PROMPT
from app.agents.tools import ToolRegistry


VISUAL_TOOL_NAMES = ["svg_visualizer", "math_plot"]


async def visual_node(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    """
    LangGraph node: Visual Agent.

    Decides which visualization tool is appropriate (SVG flowchart/DP table vs. Math coordinate plot)
    and calls it to generate structured JSON.
    """
    ctx = AgentContext(**state["context"])
    query = ctx.user_query
    subject = ctx.subject

    print(f"[VisualAgent] Processing visualization for query: '{query[:80]}...'")

    try:
        from app.services.llm_provider import get_llm_provider
        provider = get_llm_provider()

        openai_tools = ToolRegistry.get_openai_tools(VISUAL_TOOL_NAMES)
        chat_messages = [
            {"role": "system", "content": VISUAL_PROMPT},
            {"role": "user", "content": f"Determine how to visualize this query: {query}"}
        ]

        response = await provider.complete(
            model=settings.visual_model,
            messages=chat_messages,
            tools=openai_tools
        )

        tool_calls = response.get("tool_calls") or []
        viz_type = ""
        viz_data = {}

        if tool_calls:
            # Execute tool call
            tc = tool_calls[0]
            name = tc["function"]["name"]
            args = json.loads(tc["function"]["arguments"])
            
            tool = ToolRegistry.get(name)
            result = await tool.aexecute(**args)

            if name == "svg_visualizer":
                viz_data = result if isinstance(result, dict) else {}
                viz_type = viz_data.get("type", "flowchart")
            elif name == "math_plot":
                points = result if isinstance(result, list) else []
                viz_data = {
                    "type": "function_plot",
                    "expression": args.get("expression", "x"),
                    "points": points
                }
                viz_type = "function_plot"
        else:
            direct_text = response.get("text") or ""
            try:
                parsed = json.loads(direct_text.strip())
                if isinstance(parsed, dict) and "type" in parsed:
                    viz_data = parsed
                    viz_type = parsed.get("type", "flowchart")
            except:
                viz_type = "error"
                viz_data = {"message": "Failed to parse visual agent output."}

        viz_res = VisualizationResult(
            viz_type=viz_type,
            data=viz_data
        )
        print(f"[VisualAgent] Visualization complete. Type: {viz_type}")
        return {"visual_output": viz_res.model_dump()}

    except Exception as e:
        print(f"[VisualAgent] Error: {e}")
        viz_res = VisualizationResult(
            viz_type="error",
            data={"message": f"Visualization error: {e}"}
        )
        return {"visual_output": viz_res.model_dump()}
