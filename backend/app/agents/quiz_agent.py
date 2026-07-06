"""
quiz_agent.py
-------------
Quiz Agent — assessment expert.

Evaluates student capability, retrieves weak topics, and generates/sources questions.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict

from langchain_core.runnables import RunnableConfig
from app.core.config import settings
from app.agents.context import AgentContext, QuizResult
from app.agents.prompts import QUIZ_PROMPT
from app.agents.tools import ToolRegistry


QUIZ_TOOL_NAMES = ["quiz_generator", "difficulty_evaluator", "weak_topics"]


async def quiz_node(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    """
    LangGraph node: Quiz Agent.

    Uses LLM to orchestrate:
      1. Evaluating student difficulty level.
      2. Retrieving weak topics.
      3. Sourcing/generating quiz questions.
    """
    ctx = AgentContext(**state["context"])
    user_id = ctx.user_id
    subject = ctx.subject

    print(f"[QuizAgent] Formulating adaptive quiz for user {user_id} on {subject}")

    try:
        from app.services.llm_provider import get_llm_provider
        provider = get_llm_provider()

        openai_tools = ToolRegistry.get_openai_tools(QUIZ_TOOL_NAMES)
        prompt = f"Run adaptive quiz checks for user {user_id} on subject {subject}."
        chat_messages = [
            {"role": "system", "content": QUIZ_PROMPT},
            {"role": "user", "content": prompt}
        ]

        response = await provider.complete(
            model=settings.quiz_model,
            messages=chat_messages,
            tools=openai_tools
        )

        tool_calls = response.get("tool_calls") or []
        difficulty = "medium"
        weak_topics = [subject]
        quiz_data = {}

        if tool_calls:
            # ReAct Loop: Execute tools
            tool_results = {}
            for tc in tool_calls:
                name = tc["function"]["name"]
                args = json.loads(tc["function"]["arguments"])
                if "user_id" not in args:
                    args["user_id"] = user_id
                if "subject" not in args:
                    args["subject"] = subject

                tool = ToolRegistry.get(name)
                result = await tool.aexecute(**args)
                tool_results[name] = result

                if name == "difficulty_evaluator":
                    difficulty = str(result)
                elif name == "weak_topics":
                    weak_topics = result if isinstance(result, list) else [subject]
                elif name == "quiz_generator":
                    quiz_data = result if isinstance(result, dict) else {}

            # If quiz_generator was not called in the first turn, request it explicitly
            if "quiz_generator" not in tool_results:
                fn_responses = []
                for tc in tool_calls:
                    name = tc["function"]["name"]
                    fn_responses.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "name": name,
                        "content": str(tool_results[name])
                    })

                assistant_tc = [{
                    "id": tc["id"],
                    "type": "function",
                    "function": tc["function"]
                } for tc in tool_calls]

                followup_messages = [
                    {"role": "system", "content": QUIZ_PROMPT},
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": None, "tool_calls": assistant_tc}
                ] + fn_responses

                followup = await provider.complete(
                    model=settings.quiz_model,
                    messages=followup_messages,
                    tools=openai_tools
                )
                
                fc_followup = followup.get("tool_calls") or []
                if fc_followup:
                    tc = fc_followup[0]
                    name = tc["function"]["name"]
                    args = json.loads(tc["function"]["arguments"])
                    args["user_id"] = user_id
                    args["subject"] = subject
                    args["difficulty"] = difficulty
                    args["num_questions"] = 1
                    
                    tool = ToolRegistry.get(name)
                    quiz_res = await tool.aexecute(**args)
                    quiz_data = quiz_res if isinstance(quiz_res, dict) else {}
                    
                    quiz_res = await tool.aexecute(**args)
                    quiz_data = quiz_res if isinstance(quiz_res, dict) else {}
        else:
            # If no tool called, execute direct fallback
            return await _direct_quiz_fallback(ctx, user_id, subject)

        # Re-pack quiz question format
        # If it returned full generated quiz dictionary, grab the first question
        questions = quiz_data.get("questions", [])
        question_item = questions[0] if questions else quiz_data
        
        ctx.quiz = QuizResult(
            question=question_item,
            difficulty=difficulty,
            weak_topics=weak_topics
        )
        print(f"[QuizAgent] Formulated quiz successfully. Difficulty: {difficulty}")

    except Exception as e:
        print(f"[QuizAgent] Error in node: {e}")
        return await _direct_quiz_fallback(ctx, user_id, subject)

    return {"context": ctx.model_dump()}


async def _direct_quiz_fallback(ctx: AgentContext, user_id: str, subject: str) -> Dict[str, Any]:
    """Fallback: call database and generator directly without LLM orchestration."""
    try:
        diff_tool = ToolRegistry.get("difficulty_evaluator")
        weak_tool = ToolRegistry.get("weak_topics")
        gen_tool = ToolRegistry.get("quiz_generator")

        diff = await diff_tool.aexecute(user_id=user_id, subject=subject)
        weak = await weak_tool.aexecute(user_id=user_id, subject=subject)
        
        # generate 1 quick check MCQ
        quiz_data = await gen_tool.aexecute(
            user_id=user_id,
            subject=subject,
            num_questions=1,
            difficulty=str(diff)
        )
        questions = quiz_data.get("questions", [])
        question_item = questions[0] if questions else quiz_data

        ctx.quiz = QuizResult(
            question=question_item,
            difficulty=str(diff),
            weak_topics=weak if isinstance(weak, list) else [subject]
        )
    except Exception as e:
        print(f"[QuizAgent] Fallback failed: {e}")
        ctx.quiz = QuizResult(
            question={
                "question": f"Self-Check: Solve a conceptual question about {subject}.",
                "options": ["A", "B", "C", "D"],
                "correct_answer": "A",
                "explanation": "Direct fallback question."
            },
            difficulty="medium",
            weak_topics=[subject]
        )
    return {"context": ctx.model_dump()}
