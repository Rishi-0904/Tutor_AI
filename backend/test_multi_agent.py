# backend/test_multi_agent.py
import asyncio
import os
from langchain_core.messages import HumanMessage
from app.agents.context import AgentContext
from app.agents.tools import ToolRegistry
from app.services.expert_service import ExpertRegistry
from app.services.agent_service import tutor_graph


async def main():
    print("Initializing ToolRegistry and ExpertRegistry...")
    ToolRegistry.initialize()
    ExpertRegistry.initialize()

    user_query = "Explain Doppler Effect with latest ISRO applications and a diagram."
    print(f"\n--- Testing Query: '{user_query}' ---\n")

    # Initial state matching GraphState structure
    ctx = AgentContext(
        user_query=user_query,
        user_id="test_user_id_123",
        conversation_id="e1124619-a1b7-4f65-8b74-bb143cb8d15a",
        subject="physics",
        conversation_history=[]
    )

    initial_state = {
        "messages": [HumanMessage(content=user_query)],
        "context": ctx.model_dump()
    }

    # Execute graph
    print("Invoking LangGraph tutor_graph...")
    try:
        result = await tutor_graph.ainvoke(initial_state)
        final_ctx = AgentContext(**result["context"])
        
        print("\n=== EXECUTION SUCCESS ===")
        print(f"Orchestrator Intent: {final_ctx.intent}")
        print(f"Orchestrator Reasoning: {final_ctx.orchestrator_reasoning}")
        
        if final_ctx.critic_feedback:
            print(f"Critic Feedback Approved: {final_ctx.critic_feedback.approved}")
            print(f"Critic Feedback Action: {final_ctx.critic_feedback.action}")
            print(f"Critic Feedback Text: {final_ctx.critic_feedback.feedback}")
            
        print(f"Expert Used: {final_ctx.expert_used}")
        print(f"Composed Response Length: {len(final_ctx.tutor_answer)} characters")
        print("\n=== FINAL COMPOSED RESPONSE (SNEAK PEEK) ===")
        print(final_ctx.tutor_answer[:500] + "\n...")
        
    except Exception as e:
        print(f"\nError running graph: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
