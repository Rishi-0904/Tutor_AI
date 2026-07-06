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
from google import genai as google_genai
from google.genai import types

from app.core.config import settings
from app.agents.context import AgentContext, QuizResult
from app.agents.prompts import QUIZ_PROMPT
from app.agents.tools import ToolRegistry


QUIZ_TOOL_NAMES = ["quiz_generator", "difficulty_evaluator", "weak_topics"]


async def quiz_node(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    """
    LangGraph node: Quiz Agent.

    Uses Gemini to orchestrate:
      1. Evaluating student difficulty level.
      2. Retrieving weak topics.
      3. Sourcing/generating quiz questions.
    """
    ctx = AgentContext(**state["context"])
    user_id = ctx.user_id
    subject = ctx.subject

    print(f"[QuizAgent] Formulating adaptive quiz for user {user_id} on {subject}")

    api_key = settings.gemini_api_key
    if not api_key:
        # Direct fallback
        return await _direct_quiz_fallback(ctx, user_id, subject)

    client = google_genai.Client(api_key=api_key)
    quiz_tools = ToolRegistry.get_gemini_tools(QUIZ_TOOL_NAMES)

    loop = asyncio.get_running_loop()

    try:
        # Prompt Gemini to orchestrate the tools to build the quiz
        prompt = f"Run adaptive quiz checks for user {user_id} on subject {subject}."
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=QUIZ_PROMPT,
                    tools=[quiz_tools],
                ),
            ),
        )

        candidate = response.candidates[0]
        function_calls = [p.function_call for p in candidate.content.parts if p.function_call]

        difficulty = "medium"
        weak_topics = [subject]
        quiz_data = {}

        if function_calls:
            # ReAct Loop: Execute tools
            tool_results = {}
            for fc in function_calls:
                tool = ToolRegistry.get(fc.name)
                # Pass user_id and subject appropriately
                args = dict(fc.args)
                if "user_id" not in args:
                    args["user_id"] = user_id
                if "subject" not in args:
                    args["subject"] = subject

                result = await tool.aexecute(**args)
                tool_results[fc.name] = result

                if fc.name == "difficulty_evaluator":
                    difficulty = str(result)
                elif fc.name == "weak_topics":
                    weak_topics = result if isinstance(result, list) else [subject]
                elif fc.name == "quiz_generator":
                    quiz_data = result if isinstance(result, dict) else {}

            # If quiz_generator was not called in the first turn, request it explicitly
            if "quiz_generator" not in tool_results:
                # Compile turn answers to feed back to Gemini
                parts = []
                for fc in function_calls:
                    parts.append(
                        types.Part.from_function_response(
                            name=fc.name,
                            response={"result": tool_results[fc.name]}
                        )
                    )
                followup_prompt = [
                    types.Content(role="user", parts=[types.Part(text=prompt)]),
                    candidate.content,
                    types.Content(role="user", parts=parts)
                ]
                
                # Gemini will call quiz_generator now
                followup = await loop.run_in_executor(
                    None,
                    lambda: client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=followup_prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=QUIZ_PROMPT,
                            tools=[quiz_tools]
                        )
                    )
                )
                
                fc_followup = [p.function_call for p in followup.candidates[0].content.parts if p.function_call]
                if fc_followup:
                    fc = fc_followup[0]
                    tool = ToolRegistry.get(fc.name)
                    args = dict(fc.args)
                    args["user_id"] = user_id
                    args["subject"] = subject
                    args["difficulty"] = difficulty
                    args["num_questions"] = 1 # quick MCQ checks in chat node
                    
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
