"""
agent_service.py
----------------
Core agent orchestrator service for TutorAI.

Defines the true multi-agent compiled LangGraph StateGraph, registering all
agents as native graph nodes with parallel and cyclic conditional transitions.

Streams responses through an asyncio.Queue to decouple execution from SSE output.
"""

from __future__ import annotations

import asyncio
from typing import Annotated, Any, Dict, List, Sequence, Union
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from app.services.history_service import HistoryMessage
from app.agents.context import AgentContext

# Import node functions directly
from app.agents.orchestrator import orchestrator_node
from app.agents.research_agent import research_node
from app.agents.visual_agent import visual_node
from app.agents.tutor_agent import tutor_node
from app.agents.critic import critic_node
from app.agents.quiz_agent import quiz_node
from app.agents.teach_back import teach_back_node
from app.agents.roadmap import roadmap_node
from app.agents.memory import memory_node
from app.agents.composer import composer_node


# ─────────────────────────────────────────────────────────────
# STATE DEFINITION
# ─────────────────────────────────────────────────────────────

class GraphState(TypedDict):
    """LangGraph State containing active messages and shared context payload."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    context: Dict[str, Any]  # Serialized AgentContext dict


# ─────────────────────────────────────────────────────────────
# GRAPH ROUTING LOGIC
# ─────────────────────────────────────────────────────────────

def route_from_orchestrator(state: GraphState) -> Union[List[str], str]:
    """
    Conditional routing edge from Orchestrator.

    Returns the next node (or parallel nodes) to execute.
    If intent has parallel agents, returns them as a list for LangGraph fan-out.
    """
    ctx = AgentContext(**state["context"])
    intent = ctx.intent

    if "teach_back" in intent:
        return "teach_back"
    if "quiz" in intent:
        return "quiz"
    if "roadmap" in intent:
        return "roadmap"

    # Parallel branch detection for research + visual
    destinations = []
    if "research" in intent:
        destinations.append("research")
    if "visual" in intent:
        destinations.append("visual")

    if not destinations:
        return "tutor"

    return destinations  # e.g., ["research", "visual"] (parallel fan-out)


def route_from_critic(state: GraphState) -> str:
    """
    Conditional routing edge from Critic.

    Directs back to Research/Tutor if revisions are required, or forwards
    to Memory if approved.
    """
    ctx = AgentContext(**state["context"])
    fb = ctx.critic_feedback

    if fb and not fb.approved:
        if fb.action == "research":
            return "research"
        if fb.action == "revise":
            return "tutor"

    return "memory"


# ─────────────────────────────────────────────────────────────
# COMPILE GRAPH
# ─────────────────────────────────────────────────────────────

def build_tutor_graph():
    workflow = StateGraph(GraphState)

    # 1. Add all native nodes
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("research", research_node)
    workflow.add_node("visual", visual_node)
    workflow.add_node("tutor", tutor_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("quiz", quiz_node)
    workflow.add_node("roadmap", roadmap_node)
    workflow.add_node("teach_back", teach_back_node)
    workflow.add_node("memory", memory_node)
    workflow.add_node("composer", composer_node)

    # 2. Configure Entry Point and Routing Edges
    workflow.set_entry_point("orchestrator")

    # Orchestrator Conditional routing (Parallel support)
    workflow.add_conditional_edges(
        "orchestrator",
        route_from_orchestrator,
        {
            "teach_back": "teach_back",
            "quiz": "quiz",
            "roadmap": "roadmap",
            "research": "research",
            "visual": "visual",
            "tutor": "tutor"
        }
    )

    # Parallel Fan-in Joins to Tutor
    workflow.add_edge("research", "tutor")
    workflow.add_edge("visual", "tutor")

    # Tutor to Critic check
    workflow.add_edge("tutor", "critic")

    # Critic Conditional feedback loop routing (Cyclic loops)
    workflow.add_conditional_edges(
        "critic",
        route_from_critic,
        {
            "research": "research",
            "tutor": "tutor",
            "memory": "memory"
        }
    )

    # Standalone branches join directly to memory
    workflow.add_edge("teach_back", "memory")
    workflow.add_edge("quiz", "memory")
    workflow.add_edge("roadmap", "memory")

    # Final post-processing
    workflow.add_edge("memory", "composer")
    workflow.add_edge("composer", END)

    return workflow.compile()


# Compiled true multi-agent LangGraph instance
tutor_graph = build_tutor_graph()


# ─────────────────────────────────────────────────────────────
# STREAMING RUNNER
# ─────────────────────────────────────────────────────────────

async def run_agent_stream(
    conversation_id: str,
    user_id: str,
    message: str,
    subject: str,
    history: List[HistoryMessage]
):
    """
    Executes the compiled multi-agent LangGraph workflow and streams tokens.

    Streams from the shared queue populated dynamically by composer and tutor nodes.
    """
    # 1. Convert history to LangChain messages
    messages = []
    for msg in history:
        if msg.role == 'user':
            messages.append(HumanMessage(content=msg.content))
        else:
            messages.append(AIMessage(content=msg.content))
    messages.append(HumanMessage(content=message))

    # 2. Build initial typed AgentContext
    ctx = AgentContext(
        user_query=message,
        user_id=user_id,
        conversation_id=conversation_id,
        subject=subject,
        conversation_history=[{"role": msg.role, "content": msg.content} for msg in history]
    )

    initial_state = {
        "messages": messages,
        "context": ctx.model_dump()
    }

    # 3. Create execution config with streaming queue
    queue = asyncio.Queue()
    config = {
        "configurable": {
            "stream_queue": queue
        }
    }

    # 4. Launch graph execution in background
    task = asyncio.create_task(
        tutor_graph.ainvoke(initial_state, config)
    )

    # 5. Read chunks from queue and yield to stream
    while not task.done() or not queue.empty():
        try:
            chunk = await asyncio.wait_for(queue.get(), timeout=0.1)
            yield chunk
            queue.task_done()
        except asyncio.TimeoutError:
            continue

    # 6. Raise task exceptions if execution failed
    if task.done() and task.exception():
        raise task.exception()
