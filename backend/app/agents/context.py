"""
context.py
----------
Typed shared context bus for the TutorAI multi-agent system.

Every agent reads and writes through AgentContext — no random dictionary keys.
Pydantic models ensure type safety, serialization, and clear contracts between agents.
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────
# AGENT OUTPUT MODELS
# ─────────────────────────────────────────────────────────────

class ResearchResult(BaseModel):
    """Structured output from the Research Agent."""
    web_summary: str = ""
    citations: List[str] = Field(default_factory=list)
    youtube_links: str = ""


class VisualizationResult(BaseModel):
    """Structured output from the Visual Agent."""
    viz_type: str = ""          # "function_plot" | "flowchart" | "dp_table" | ""
    data: Dict[str, Any] = Field(default_factory=dict)


class QuizResult(BaseModel):
    """Structured output from the Quiz Agent."""
    question: Dict[str, Any] = Field(default_factory=dict)
    difficulty: str = "medium"
    weak_topics: List[str] = Field(default_factory=list)


class TeachBackResult(BaseModel):
    """Structured output from the Teach-Back evaluation."""
    score: int = 0
    coverage: List[str] = Field(default_factory=list)
    missing_concepts: List[str] = Field(default_factory=list)
    misconceptions: List[str] = Field(default_factory=list)
    confidence: str = "Medium"
    feedback: str = ""
    concept: str = ""


class RoadmapResult(BaseModel):
    """Structured output from the Roadmap service."""
    steps: List[Dict[str, Any]] = Field(default_factory=list)


class CriticFeedback(BaseModel):
    """Structured feedback from the Critic Agent."""
    approved: bool = True
    feedback: str = ""
    action: str = "approve"  # "approve" | "research" | "revise"
    missing_elements: List[str] = Field(default_factory=list)


class ExecutionPlan(BaseModel):
    """Deterministic execution schedule produced by the Planner."""
    parallel: List[str] = Field(default_factory=list)       # agents that run concurrently
    sequential: List[str] = Field(default_factory=list)     # agents that run after parallel phase
    post_processing: List[str] = Field(default_factory=lambda: ["memory", "composer"])


# ─────────────────────────────────────────────────────────────
# SHARED CONTEXT BUS
# ─────────────────────────────────────────────────────────────

class AgentContext(BaseModel):
    """
    Shared typed context bus.

    Every agent reads and writes only through this model.
    Serialized as a dict inside the LangGraph GraphState TypedDict.
    """

    # ── Input (set once at the start) ──
    user_query: str = ""
    user_id: str = ""
    conversation_id: str = ""
    subject: str = "general"

    # ── Orchestrator output ──
    intent: List[str] = Field(default_factory=list)         # e.g. ["tutor", "visual"]
    orchestrator_reasoning: str = ""

    # ── Execution plan (set by planner) ──
    execution_plan: Optional[ExecutionPlan] = None

    # ── Agent outputs ──
    research: Optional[ResearchResult] = None
    visualization: Optional[VisualizationResult] = None
    quiz: Optional[QuizResult] = None
    teach_back: Optional[TeachBackResult] = None
    roadmap: Optional[RoadmapResult] = None
    tutor_answer: str = ""
    topic_tags: List[str] = Field(default_factory=list)
    expert_used: str = "gemini"
    
    # ── Critic output ──
    critic_feedback: Optional[CriticFeedback] = None

    # ── Memory flags (set by agents, consumed by memory service) ──
    mastery_changed: bool = False
    mastery_updates: List[Dict[str, Any]] = Field(default_factory=list)
    is_correct: Optional[bool] = None

    # ── Metadata (extensible dict for planner/executor internals) ──
    metadata: Dict[str, Any] = Field(default_factory=dict)
