# backend/app/agents/__init__.py
"""
TutorAI Multi-Agent System
--------------------------
Hybrid multi-agent architecture powered by LangGraph.

LLM Agents (autonomous reasoning):
  - Orchestrator: Intent classification
  - Tutor: Educational expert with ReAct tool calling
  - Research: Web search specialist
  - Visual: Visualization specialist
  - Quiz: Assessment expert

Deterministic Nodes (no LLM cost):
  - Planner: Execution scheduling
  - Teach-Back: Evaluation service wrapper
  - Roadmap: DB service wrapper
  - Memory: Conditional DB updates
  - Composer: Markdown assembly
"""
