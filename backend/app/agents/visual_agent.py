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
from google import genai as google_genai
from google.genai import types

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

    api_key = settings.gemini_api_key
    if not api_key:
        # Fallback: return default error result
        ctx.visualization = VisualizationResult(
            viz_type="error",
            data={"message": "Gemini API key missing. Visual tools offline."}
        )
        return {"context": ctx.model_dump()}

    client = google_genai.Client(api_key=api_key)
    visual_tools = ToolRegistry.get_gemini_tools(VISUAL_TOOL_NAMES)

    loop = asyncio.get_running_loop()

    try:
        # Call Gemini to decide what type of visualization fits and invoke the tool
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"Determine how to visualize this query: {query}",
                config=types.GenerateContentConfig(
                    system_instruction=VISUAL_PROMPT,
                    tools=[visual_tools],
                ),
            ),
        )

        candidate = response.candidates[0]
        function_calls = [p.function_call for p in candidate.content.parts if p.function_call]

        viz_type = ""
        viz_data = {}

        if function_calls:
            # Execute tool call
            fc = function_calls[0]
            tool = ToolRegistry.get(fc.name)
            args = dict(fc.args)

            result = await tool.aexecute(**args)

            if fc.name == "svg_visualizer":
                viz_data = result if isinstance(result, dict) else {}
                viz_type = viz_data.get("type", "flowchart")
            elif fc.name == "math_plot":
                # If math_plot runs, we return a function_plot type wrapper
                points = result if isinstance(result, list) else []
                viz_data = {
                    "type": "function_plot",
                    "expression": args.get("expression", "x"),
                    "points": points
                }
                viz_type = "function_plot"
        else:
            # Fallback if LLM generated content directly instead of calling tools
            # Let's inspect the text response
            direct_text = response.text or ""
            try:
                # Try parsing if it's a JSON block
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
