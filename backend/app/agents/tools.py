"""
tools.py
--------
Tool Layer for TutorAI multi-agent system.

Wraps existing service functions as tools that agents invoke via Gemini's
function-calling API (ReAct pattern). Each tool is a thin wrapper with:
  - name + description (for LLM tool selection)
  - parameter schema (for Gemini FunctionDeclaration)
  - execute() method (calls the underlying service)

Agents don't call services directly — they invoke tools.
"""

from __future__ import annotations

import json
import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from google.genai import types


# ─────────────────────────────────────────────────────────────
# TOOL DEFINITION
# ─────────────────────────────────────────────────────────────

@dataclass
class ToolDefinition:
    """
    A tool that an agent can invoke.

    Attributes:
        name:        Unique tool identifier (used by Gemini function calling).
        description: Human-readable description (sent to LLM for tool selection).
        parameters:  JSON-Schema dict describing the tool's parameters.
        fn:          The actual Python function to execute.
        is_async:    Whether fn is an async function.
    """
    name: str
    description: str
    parameters: Dict[str, Any]
    fn: Callable
    is_async: bool = False

    def to_openai_tool(self) -> dict:
        """Convert to standard OpenAI function tool schema."""
        properties = {}
        for prop_name, prop_schema in self.parameters.get("properties", {}).items():
            properties[prop_name] = {
                "type": prop_schema.get("type", "string"),
                "description": prop_schema.get("description", "")
            }
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": self.parameters.get("required", [])
                }
            }
        }

    def to_gemini_declaration(self) -> types.FunctionDeclaration:
        """Convert to Gemini's FunctionDeclaration format."""
        properties = {}
        required = self.parameters.get("required", [])

        for prop_name, prop_schema in self.parameters.get("properties", {}).items():
            prop_type = prop_schema.get("type", "string").upper()
            gemini_type = getattr(types.Type, prop_type, types.Type.STRING)
            properties[prop_name] = types.Schema(
                type=gemini_type,
                description=prop_schema.get("description", ""),
            )

        return types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties=properties,
                required=required,
            ),
        )

    def execute(self, **kwargs) -> Any:
        """Execute the underlying function synchronously."""
        return self.fn(**kwargs)

    async def aexecute(self, **kwargs) -> Any:
        """Execute the underlying function, handling both sync and async fns."""
        if self.is_async:
            return await self.fn(**kwargs)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: self.fn(**kwargs))


# ─────────────────────────────────────────────────────────────
# TOOL REGISTRY
# ─────────────────────────────────────────────────────────────

class ToolRegistry:
    """
    Singleton registry for all tools.

    Usage:
        ToolRegistry.register(my_tool)
        tool = ToolRegistry.get("my_tool")
        result = await tool.aexecute(question="...")

        # Get Gemini-compatible tool declarations for specific tools
        gemini_tools = ToolRegistry.get_gemini_tools(["physics_lora", "math_lora"])
    """
    _tools: Dict[str, ToolDefinition] = {}

    @classmethod
    def register(cls, tool: ToolDefinition) -> None:
        cls._tools[tool.name] = tool

    @classmethod
    def get(cls, name: str) -> ToolDefinition:
        if name not in cls._tools:
            raise ValueError(f"Tool '{name}' not registered. Available: {list(cls._tools.keys())}")
        return cls._tools[name]

    @classmethod
    def has(cls, name: str) -> bool:
        return name in cls._tools

    @classmethod
    def get_openai_tools(cls, names: List[str]) -> List[dict]:
        """Build standard OpenAI tool schemas for the given tool names."""
        return [cls._tools[n].to_openai_tool() for n in names if n in cls._tools]

    @classmethod
    def get_gemini_tools(cls, names: List[str]) -> types.Tool:
        """Build a Gemini Tool object containing declarations for the given tool names."""
        declarations = [cls._tools[n].to_gemini_declaration() for n in names if n in cls._tools]
        return types.Tool(function_declarations=declarations)

    @classmethod
    def list_tools(cls) -> List[str]:
        return list(cls._tools.keys())

    @classmethod
    def initialize(cls) -> None:
        """Register all built-in tools. Call once at startup."""
        if cls._tools:
            return  # already initialized

        for tool in _build_all_tools():
            cls.register(tool)
        print(f"[ToolRegistry] Initialized {len(cls._tools)} tools: {cls.list_tools()}")


# ─────────────────────────────────────────────────────────────
# TOOL DEFINITIONS
# ─────────────────────────────────────────────────────────────

def _build_all_tools() -> List[ToolDefinition]:
    """Construct all tool definitions, wrapping existing service functions."""
    tools = []

    # ── Subject Expert Tools (LoRA) ──────────────────────────
    tools.append(_build_lora_tool(
        name="physics_lora",
        subject="physics",
        description=(
            "Solve a numerical physics problem using the Physics LoRA expert. "
            "Use for problems involving forces, motion, energy, circuits, optics, "
            "thermodynamics, waves, modern physics, etc."
        ),
    ))
    tools.append(_build_lora_tool(
        name="math_lora",
        subject="mathematics",
        description=(
            "Solve a numerical mathematics problem using the Math LoRA expert. "
            "Use for calculus, algebra, coordinate geometry, probability, matrices, "
            "complex numbers, differential equations, etc."
        ),
    ))
    tools.append(_build_lora_tool(
        name="chemistry_lora",
        subject="chemistry",
        description=(
            "Solve a numerical chemistry problem using the Chemistry LoRA expert. "
            "Use for stoichiometry, equilibrium, electrochemistry, organic reactions, "
            "thermochemistry, atomic structure, etc."
        ),
    ))

    # ── Search Tools ─────────────────────────────────────────
    tools.append(ToolDefinition(
        name="google_search",
        description=(
            "Search the web for current information, exam dates, syllabus changes, "
            "recent news, or any live data."
        ),
        parameters={
            "properties": {
                "query": {"type": "string", "description": "The search query"},
            },
            "required": ["query"],
        },
        fn=_google_search_fn,
        is_async=True,
    ))
    tools.append(ToolDefinition(
        name="youtube_search",
        description="Find relevant YouTube lecture videos for a topic.",
        parameters={
            "properties": {
                "query": {"type": "string", "description": "The search query for YouTube"},
            },
            "required": ["query"],
        },
        fn=_youtube_search_fn,
        is_async=True,
    ))

    # ── Visualization Tools ──────────────────────────────────
    tools.append(ToolDefinition(
        name="svg_visualizer",
        description=(
            "Generate a flowchart, concept map, DP table, or function plot "
            "as structured JSON for rendering."
        ),
        parameters={
            "properties": {
                "prompt": {"type": "string", "description": "What to visualize"},
                "subject": {"type": "string", "description": "The subject area (physics, chemistry, mathematics, general)"},
            },
            "required": ["prompt", "subject"],
        },
        fn=_svg_visualizer_fn,
    ))
    tools.append(ToolDefinition(
        name="math_plot",
        description=(
            "Evaluate a math expression and return (x,y) coordinate arrays for plotting. "
            "Expression uses Python syntax with variable x, e.g. 'x**2 - 4*x' or 'math.sin(x)'."
        ),
        parameters={
            "properties": {
                "expression": {"type": "string", "description": "Math expression in Python syntax using variable x"},
            },
            "required": ["expression"],
        },
        fn=_math_plot_fn,
    ))

    # ── Assessment Tools ─────────────────────────────────────
    tools.append(ToolDefinition(
        name="quiz_generator",
        description="Generate adaptive MCQ questions targeting weak topics.",
        parameters={
            "properties": {
                "user_id": {"type": "string", "description": "Student user ID"},
                "subject": {"type": "string", "description": "Subject for the quiz"},
                "num_questions": {"type": "integer", "description": "Number of questions to generate"},
                "difficulty": {"type": "string", "description": "Difficulty level: easy, medium, or hard"},
            },
            "required": ["user_id", "subject"],
        },
        fn=_quiz_generator_fn,
    ))
    tools.append(ToolDefinition(
        name="difficulty_evaluator",
        description="Evaluate the student's difficulty level from past quiz attempts.",
        parameters={
            "properties": {
                "user_id": {"type": "string", "description": "Student user ID"},
                "subject": {"type": "string", "description": "Subject to evaluate"},
            },
            "required": ["user_id", "subject"],
        },
        fn=_difficulty_evaluator_fn,
    ))

    # ── Data Access Tools ────────────────────────────────────
    tools.append(ToolDefinition(
        name="weak_topics",
        description="Get the student's weakest topics in a subject for personalization.",
        parameters={
            "properties": {
                "user_id": {"type": "string", "description": "Student user ID"},
                "subject": {"type": "string", "description": "Subject to check"},
            },
            "required": ["user_id", "subject"],
        },
        fn=_weak_topics_fn,
    ))
    tools.append(ToolDefinition(
        name="pdf_search",
        description=(
            "Semantic vector search across the student's uploaded PDF notes and textbooks. "
            "Use when the student references their notes or when additional context from "
            "their materials would help."
        ),
        parameters={
            "properties": {
                "query": {"type": "string", "description": "Search query for the student's documents"},
                "user_id": {"type": "string", "description": "Student user ID"},
            },
            "required": ["query", "user_id"],
        },
        fn=_pdf_search_fn,
        is_async=True,
    ))

    return tools


# ─────────────────────────────────────────────────────────────
# TOOL IMPLEMENTATIONS (thin wrappers around existing services)
# ─────────────────────────────────────────────────────────────

def _build_lora_tool(name: str, subject: str, description: str) -> ToolDefinition:
    """Factory for LoRA expert tools (Mocked for testing without GPU)."""
    def _lora_fn(question: str) -> dict:
        print(f"[LoRA Mock Tool] Mocking LoRA call for {subject} with query: '{question}'")
        # Return a mock ExpertResult dictionary structure
        return {
            "answer": (
                f"**[Mocked {subject.capitalize()} Expert Answer]**\n"
                f"To solve: {question}\n\n"
                f"Step 1: Identify key equations for {subject}.\n"
                f"Step 2: Substitute parameters and simplify.\n\n"
                f"We wrap the final mock result in LaTeX: \\boxed{{42}}."
            ),
            "reasoning_steps": "Mocked reasoning steps showing the conceptual breakdown.",
            "final_result": "42",
            "confidence": 0.95,
            "expert_used": f"{subject}_lora_mocked"
        }

    return ToolDefinition(
        name=name,
        description=description,
        parameters={
            "properties": {
                "question": {"type": "string", "description": f"The {subject} problem to solve"},
            },
            "required": ["question"],
        },
        fn=_lora_fn,
    )


async def _google_search_fn(query: str) -> str:
    from app.services.mcp_service import web_search_tool
    return await web_search_tool(query)


async def _youtube_search_fn(query: str) -> str:
    from app.services.mcp_service import youtube_search_tool
    return await youtube_search_tool(query)


def _svg_visualizer_fn(prompt: str, subject: str) -> dict:
    from app.services.visualizer_service import generate_visual_data
    return generate_visual_data(prompt, subject)


def _math_plot_fn(expression: str) -> list:
    from app.services.visualizer_service import evaluate_math_expression
    return evaluate_math_expression(expression)


def _quiz_generator_fn(
    user_id: str,
    subject: str,
    num_questions: int = 5,
    difficulty: Optional[str] = None,
) -> dict:
    from app.services.quiz_service import generate_adaptive_quiz
    return generate_adaptive_quiz(user_id, subject, num_questions, difficulty)


def _difficulty_evaluator_fn(user_id: str, subject: str) -> str:
    from app.services.quiz_service import evaluate_student_difficulty
    return evaluate_student_difficulty(user_id, subject)


def _weak_topics_fn(user_id: str, subject: str) -> list:
    from app.services.weakness_service import get_top_weak_topics
    return get_top_weak_topics(user_id, subject, n=3)


async def _pdf_search_fn(query: str, user_id: str) -> str:
    from app.services.mcp_service import mcp_service
    return await mcp_service.search_pdf(query, user_id)


# ─────────────────────────────────────────────────────────────
# STREAMING UTILITIES
# ─────────────────────────────────────────────────────────────

async def stream_sync_to_queue(sync_gen, queue: Optional[asyncio.Queue]) -> str:
    """
    Run a synchronous generator in a thread, pushing each chunk
    to an asyncio.Queue in real-time. Returns the full concatenated text.

    Used for streaming generate_answer_stream() output through the
    LangGraph pipeline. Supports None queue for non-streaming executions.
    """
    loop = asyncio.get_running_loop()
    full_parts: List[str] = []

    def _produce():
        for chunk in sync_gen:
            full_parts.append(chunk)
            if queue is not None:
                loop.call_soon_threadsafe(queue.put_nowait, chunk)

    await loop.run_in_executor(None, _produce)
    return "".join(full_parts)
