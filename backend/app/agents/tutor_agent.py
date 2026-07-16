"""
tutor_agent.py
--------------
Tutor Agent — the main educational expert with ReAct tool calling.

Replaces: subject_router_node, expert_node, tutor_node.

Uses Gemini with function-calling to naturally select the right tool:
  Thought: This is a physics numerical problem.
  Tool: physics_grpo(question="...")
  Observation: {answer: "...", confidence: 0.87}
  Thought: High confidence. Format this answer.
  Finish: [formatted response with LaTeX]

For conceptual questions, answers directly without tools.
Streams the response token-by-token via asyncio.Queue.
"""

from __future__ import annotations

import json
import asyncio
from typing import Any, Dict, List

from langchain_core.runnables import RunnableConfig
from app.core.config import settings
from app.agents.context import AgentContext
from app.agents.prompts import TUTOR_PROMPT, TEACH_BACK_INVITATION
from app.agents.tools import ToolRegistry, stream_sync_to_queue
from app.services.expert_service import CONFIDENCE_THRESHOLD


# Tools the Tutor Agent can invoke
TUTOR_TOOL_NAMES = [
    "physics_grpo",
    "math_grpo",
    "chemistry_grpo",
    "pdf_search",
    "weak_topics",
]


def _build_tutor_context(ctx: AgentContext) -> str:
    """
    Build the augmented user prompt with context from other agents
    (research results, visualization data, weak topics, etc.)
    """
    parts = []

    # Inject research context if available
    if ctx.research and ctx.research.web_summary:
        parts.append(
            f"[Research Context]\n{ctx.research.web_summary}"
        )
        if ctx.research.youtube_links:
            parts.append(
                f"[YouTube Resources]\n{ctx.research.youtube_links}"
            )

    # Inject visualization reference if available
    if ctx.visualization and ctx.visualization.data:
        parts.append(
            f"[Visualization Generated]\n"
            f"A {ctx.visualization.viz_type} visualization has been generated for the student. "
            f"Reference it in your explanation."
        )

    # The actual user query
    parts.append(f"Student's question: {ctx.user_query}")

    return "\n\n".join(parts)


async def tutor_node(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    """
    LangGraph node: Tutor Agent.

    Streams its response through config["configurable"]["stream_queue"].
    Uses Gemini function-calling for ReAct-style tool invocation.
    """
    ctx = AgentContext(**state["context"])
    
    # Load parallel outputs from state if available
    from app.agents.context import ResearchResult, VisualizationResult
    if state.get("research_output"):
        ctx.research = ResearchResult(**state["research_output"])
    if state.get("visual_output"):
        ctx.visualization = VisualizationResult(**state["visual_output"])
        
    queue = config.get("configurable", {}).get("stream_queue")

    api_key = settings.gemini_api_key
    if not api_key:
        error_msg = (
            "System Error: `GEMINI_API_KEY` is not set in `.env`. "
            "Please add it and restart the server.\n"
        )
        ctx.tutor_answer = error_msg
        if queue:
            await queue.put(error_msg)
        return {"context": ctx.model_dump()}

    user_content = _build_tutor_context(ctx)

    # Build OpenAI tool declarations
    openai_tools = ToolRegistry.get_openai_tools(TUTOR_TOOL_NAMES)

    print(f"[TutorAgent] Processing: '{ctx.user_query[:80]}...'")

    try:
        from app.services.llm_provider import get_llm_provider
        provider = get_llm_provider()

        chat_messages = [
            {"role": "system", "content": TUTOR_PROMPT},
            {"role": "user", "content": user_content}
        ]

        response = await provider.complete(
            model=settings.tutor_model,
            messages=chat_messages,
            tools=openai_tools
        )
    except Exception as e:
        error_msg = f"\n\nError communicating with LLM Provider: {str(e)}\n"
        ctx.tutor_answer = error_msg
        if queue:
            await queue.put(error_msg)
        return {"context": ctx.model_dump()}

    tool_calls = response.get("tool_calls") or []
    direct_text = response.get("text") or ""

    full_response = ""
    expert_used = "gemini"

    if tool_calls:
        # ── Tool-calling path (ReAct) ──
        print(f"[TutorAgent] Tool calls requested: {[tc['function']['name'] for tc in tool_calls]}")

        tool_results = {}
        raw_answer = ""

        for tc in tool_calls:
            tool_name = tc["function"]["name"]
            tool_args = json.loads(tc["function"]["arguments"])
            
            # Auto-inject user_id if expected by the tool but not provided by LLM
            if "user_id" not in tool_args:
                tool_args["user_id"] = ctx.user_id
                
            print(f"[TutorAgent] Executing tool: {tool_name}({tool_args})")

            try:
                tool = ToolRegistry.get(tool_name)
                # LoRA tools are CPU-bound → run in executor
                result = await tool.aexecute(**tool_args)
                tool_results[tool_name] = result
                print(f"[TutorAgent] Tool {tool_name} returned: {type(result)}")

                if isinstance(result, dict) and result.get("answer"):
                    raw_answer = result["answer"]
                    expert_used = result.get("expert_used", tool_name)
            except Exception as e:
                print(f"[TutorAgent] Tool {tool_name} error: {e}")
                tool_results[tool_name] = {"error": str(e)}

        # Check confidence from LoRA results
        confidence = 0
        for tc in tool_calls:
            r = tool_results.get(tc["function"]["name"], {})
            if isinstance(r, dict):
                confidence = max(confidence, r.get("confidence", 0))

        if raw_answer and confidence >= CONFIDENCE_THRESHOLD:
            # ── High-confidence LoRA answer → format via generate_answer_stream ──
            if queue:
                label = expert_used.replace("_", " ").title()
                await queue.put(f"*(🔬 {label} active...)*\\n\\n")

            from app.services.llm_service import generate_answer_stream
            gen = generate_answer_stream(ctx.user_query, [], ctx.subject, raw_answer)
            full_response = await stream_sync_to_queue(gen, queue)

        else:
            # ── Low confidence or non-answer tool → send results back to LLM ──
            if queue:
                await queue.put("*(Thinking...)*\\n\\n")

            # Build multi-turn messages log with tool responses
            assistant_tc = [{
                "id": tc["id"],
                "type": "function",
                "function": tc["function"]
            } for tc in tool_calls]

            fn_responses = []
            for tc in tool_calls:
                name = tc["function"]["name"]
                fn_responses.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "name": name,
                    "content": json.dumps(tool_results.get(name, {}), default=str)
                })

            followup_messages = [
                {"role": "system", "content": TUTOR_PROMPT},
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": None, "tool_calls": assistant_tc}
            ] + fn_responses

            if queue:
                full_response = await provider.complete_stream(
                    model=settings.tutor_model,
                    messages=followup_messages,
                    queue=queue
                )
            else:
                followup = await provider.complete(
                    model=settings.tutor_model,
                    messages=followup_messages
                )
                full_response = followup.get("text") or ""

    else:
        # ── Conceptual path (no tool call) — Gemini answered directly ──
        if direct_text:
            # Stream the direct answer via generate_answer_stream for consistent formatting
            if queue:
                await queue.put("*(Thinking...)*\\n\\n")

            from app.services.llm_service import generate_answer_stream
            gen = generate_answer_stream(ctx.user_query, [], ctx.subject, direct_text)
            full_response = await stream_sync_to_queue(gen, queue)
        else:
            full_response = "I'm unable to generate a response at this time."
            if queue:
                await queue.put(full_response)

    # ── Post-processing ──
    from app.services.llm_service import extract_topic_tags
    topic_tags = extract_topic_tags(ctx.user_query, full_response)

    # Teach-back invitation for conceptual answers (no tool calls, no quiz/roadmap/teach_back)
    non_invitable = {"quiz", "roadmap", "teach_back"}
    should_invite = (
        not tool_calls
        and not any(a in ctx.intent for a in non_invitable)
    )
    if should_invite:
        full_response += TEACH_BACK_INVITATION
        if queue:
            await queue.put(TEACH_BACK_INVITATION)

    ctx.tutor_answer = full_response
    ctx.topic_tags = topic_tags
    ctx.expert_used = expert_used

    return {"context": ctx.model_dump()}
