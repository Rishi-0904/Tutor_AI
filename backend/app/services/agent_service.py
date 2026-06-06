import os
import json
import asyncio
from typing import Dict, Any, List, Optional, Union, Annotated, Sequence
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from google import genai as google_genai
from google.genai import types
from app.core.supabase_client import supabase

from app.core.config import settings
from app.services.llm_service import (
    generate_answer, 
    generate_answer_stream, 
    route_question, 
    SUBJECT_SYSTEM_PROMPTS
)
from app.services.mcp_service import (
    web_search_tool, 
    youtube_search_tool, 
    code_executor_tool
)
from app.services.history_service import HistoryMessage, save_assistant_message
from app.services.weakness_service import get_top_weak_topics
from app.services.expert_service import (
    ExpertRegistry,
    detect_question_type,
    CONFIDENCE_THRESHOLD,
)

# =====================================================================
# AGENT STATE DEFINITION
# =====================================================================

class TutorAgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    subject: str
    user_id: str
    conversation_id: str
    topic_tags: List[str]
    weak_topics: List[str]
    research_results: Optional[str]
    visualization_data: Optional[Dict[str, Any]]
    quiz_data: Optional[Dict[str, Any]]
    suggested_videos: Optional[str]
    roadmap_steps: Optional[List[Dict[str, Any]]]
    teach_back_data: Optional[Dict[str, Any]]
    next_node: str
    # LoRA expert routing fields
    question_type: str                   # "numerical" | "conceptual" | "ambiguous"
    expert_result: Optional[Dict[str, Any]]  # ExpertResult.to_dict() if LoRA ran
    expert_used: str                     # "physics_lora" | "math_lora" | "chem_lora" | "gemini"

# =====================================================================
# AGENT NODES
# =====================================================================

async def router_node(state: TutorAgentState) -> Dict[str, Any]:
    """
    Analyzes user intent and routes to the appropriate agent.
    - If user wants a plot or graph -> Visualizer Node
    - If user asks for external information/web search/facts -> Research Node
    - If user wants a quick quiz or is answering a quiz -> Quiz Node
    - Otherwise -> Tutor Node (Instruction)
    """
    last_message = state["messages"][-1].content.lower()
    
    # 1. Check for visual request keywords
    visual_keywords = [
        "plot", "graph", "draw", "visualize", "diagram", "sketch", "show curve",
        "flowchart", "concept map", "logic map", "logical tree", "binary tree", 
        "dp table", "dynamic programming table", "dfs path", "bfs path"
    ]
    if any(k in last_message for k in visual_keywords):
        return {"next_node": "visualizer"}
        
    # 2. Check for external research keywords
    research_keywords = ["latest news", "search", "web", "news", "recent", "exam date", "google", "find info on"]
    if any(k in last_message for k in research_keywords):
        return {"next_node": "research"}
        
    # 3. Check for quiz request keywords
    quiz_keywords = ["quiz", "test me", "question", "give me a problem", "solve a quiz"]
    if any(k in last_message for k in quiz_keywords):
        return {"next_node": "quiz"}
        
    # 4. Check for roadmap request keywords
    roadmap_keywords = ["roadmap", "syllabus", "study plan", "learning path", "what next", "what should i study"]
    if any(k in last_message for k in roadmap_keywords):
        return {"next_node": "roadmap"}
        
    # 5. Check for teach-back request keywords or context-based active recall triggers
    teach_back_keywords = ["let me explain", "my understanding is", "teach back", "explain back", "so basically", "so according to this"]
    if any(k in last_message for k in teach_back_keywords):
        return {"next_node": "teach_back"}
        
    # Check if the last assistant message in history was a teach-back invitation
    last_ai_message = None
    for msg in reversed(state["messages"][:-1]):
        if isinstance(msg, AIMessage):
            last_ai_message = msg.content
            break
            
    if last_ai_message and "Would you like to explain this concept back to me" in last_ai_message:
        # User is responding to a teach-back prompt. Make sure it's not a refusal or question.
        declines = ["no", "no thanks", "nope", "not now", "skip", "don't want to", "explain more", "next topic", "sorry"]
        is_refusal = any(last_message.strip().startswith(d) for d in declines)
        is_short_question = (last_message.endswith("?") and len(last_message.split()) < 6)
        
        if not is_refusal and not is_short_question:
            return {"next_node": "teach_back"}
        
    return {"next_node": "tutor"}


async def research_node(state: TutorAgentState) -> Dict[str, Any]:
    """Runs MCP tools or Gemini Search Grounding to extract external web/YouTube context."""
    last_message = state["messages"][-1].content
    print(f"[Agentic Research] Fetching background material for query: '{last_message}'")
    
    # Run Web Search and YouTube search in parallel to keep things snappy
    web_task = web_search_tool(last_message)
    yt_task = youtube_search_tool(last_message)
    web_results, yt_results = await asyncio.gather(web_task, yt_task)
    
    return {
        "research_results": web_results,
        "suggested_videos": yt_results,
        "next_node": "tutor" # Route to tutor to explain findings
    }


async def visualizer_node(state: TutorAgentState) -> Dict[str, Any]:
    """Generates visual structured data for rendering in the frontend."""
    last_message = state["messages"][-1].content
    subject = state["subject"]
    print(f"[Agentic Visualizer] Formulating visual data for query: '{last_message}'")
    
    from app.services.visualizer_service import generate_visual_data
    visual_data = generate_visual_data(last_message, subject)
    
    return {
        "visualization_data": visual_data,
        "next_node": "tutor"
    }


async def quiz_node(state: TutorAgentState) -> Dict[str, Any]:
    """Handles formative assessment check-in questions."""
    user_id = state["user_id"]
    subject = state["subject"]
    
    # Evaluate dynamic difficulty level
    from app.services.quiz_service import evaluate_student_difficulty
    difficulty = evaluate_student_difficulty(user_id, subject)
    
    # Generate 1 quick quiz question based on weak topics
    weak_topics = get_top_weak_topics(user_id, subject, n=1)
    topics_str = weak_topics[0] if weak_topics else subject
    
    api_key = settings.gemini_api_key
    quiz_question = {
        "question": f"Quick Check: Solve a conceptual question about {topics_str} ({difficulty} level).",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "correct": "A",
        "explanation": "No custom explanation loaded."
    }
    
    if api_key:
        try:
            client = google_genai.Client(api_key=api_key)
            prompt = f"""Generate exactly one IIT-JEE level multiple choice question on the topic: {topics_str}.
Target difficulty: {difficulty.upper()} (EASY = direct formulas, MEDIUM = JEE Main level, HARD = JEE Advanced multi-step problems).
Return ONLY a valid JSON object matching this schema:
{{
  "question": "...",
  "options": ["A", "B", "C", "D"],
  "correct": "A",
  "explanation": "..."
}}
"""
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            if response and response.text:
                quiz_question = json.loads(response.text.strip())
        except Exception as e:
            print(f"[Quiz Node] Failed to generate agentic quiz: {e}")
            
    return {
        "quiz_data": quiz_question,
        "next_node": "tutor"
    }


async def roadmap_node(state: TutorAgentState) -> Dict[str, Any]:
    """Retrieves and updates the user's learning roadmap."""
    user_id = state["user_id"]
    subject = state["subject"]
    print(f"[Agentic Roadmap] Retrieving study roadmap for subject: {subject}")
    
    from app.services.roadmap_service import get_or_create_roadmap
    steps = get_or_create_roadmap(user_id, subject)
    
    return {
        "roadmap_steps": steps,
        "next_node": "tutor"
    }


async def teach_back_node(state: TutorAgentState) -> Dict[str, Any]:
    """Evaluates student's active recall explanation."""
    user_id = state["user_id"]
    messages = state["messages"]
    last_explanation = messages[-1].content
    
    # Extract concept from active history using LLM context analyzer
    concept = state["subject"]
    api_key = settings.gemini_api_key
    if api_key and len(messages) > 1:
        try:
            history_text = "\n".join(f"{type(m).__name__}: {m.content}" for m in messages[-4:-1])
            client = google_genai.Client(api_key=api_key)
            prompt = (
                f"Conversation context:\n{history_text}\n\n"
                "Identify the specific scientific, mathematical, or chemical concept currently being discussed "
                "(e.g. 'Newton's Third Law', 'Stoichiometry', 'Integration by Parts'). "
                "Return ONLY the plain concept name."
            )
            response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            if response and response.text:
                concept = response.text.strip()
        except Exception as e:
            print(f"[Teach-Back Node] Error extracting concept: {e}")
            
    from app.services.teach_back_service import evaluate_student_explanation
    eval_res = evaluate_student_explanation(concept, last_explanation)
    eval_res["concept"] = concept
    
    return {
        "teach_back_data": eval_res,
        "next_node": "tutor"
    }


async def subject_router_node(state: TutorAgentState) -> Dict[str, Any]:
    """
    Second-level router that fires after the intent router decides on 'tutor'.
    Detects:
      1. Subject (physics / chemistry / mathematics / general) via route_question()
      2. Question type (numerical / conceptual / ambiguous) via detect_question_type()
    Routes to 'expert' node.
    """
    from app.services.llm_service import route_question
    question = state["messages"][-1].content
    subject       = route_question(question)
    question_type = detect_question_type(question)
    print(f"[SubjectRouter] subject={subject} | type={question_type}")
    return {
        "subject": subject,
        "question_type": question_type,
        "next_node": "expert"
    }


async def expert_node(state: TutorAgentState) -> Dict[str, Any]:
    """
    Dispatches to the appropriate LoRA expert or GeminiTutor.

    Rules:
      - numerical + known subject  → LoRAExpert (physics/chem/math)
      - conceptual / ambiguous     → GeminiTutor (no LoRA call)
      - LoRA confidence < threshold → fallback to GeminiTutor

    The result is stored in state['expert_result'] so run_agent_stream()
    can use the LoRA answer as raw_answer for Gemini formatting.
    """
    question      = state["messages"][-1].content
    subject       = state.get("subject", "general")
    question_type = state.get("question_type", "ambiguous")
    history       = []  # history is passed via state messages

    # Build learning context string from state for personalisation
    learning_context = None
    weak = state.get("weak_topics", [])
    if weak:
        learning_context = f"Student weak topics: {', '.join(weak)}"

    registry = ExpertRegistry.get()

    if question_type == "numerical" and subject in ("physics", "chemistry", "mathematics", "maths", "math"):
        expert = registry.get_expert(subject)
        loop   = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(
                None,
                expert.generate,
                question,
                history,
                learning_context,
            )
            if result.confidence >= CONFIDENCE_THRESHOLD:
                print(f"[Expert] {result.expert_used} answered (conf={result.confidence:.2f}) ✓")
                return {
                    "expert_result": result.to_dict(),
                    "expert_used": result.expert_used,
                    "next_node": "tutor"
                }
            else:
                print(f"[Expert] confidence {result.confidence:.2f} < {CONFIDENCE_THRESHOLD} — falling back to Gemini")
        except Exception as e:
            print(f"[Expert] LoRA generation error: {e} — falling back to Gemini")
    else:
        print(f"[Expert] question_type='{question_type}' → gemini (no LoRA needed)")

    # Gemini path (conceptual / ambiguous / fallback)
    return {
        "expert_result": None,
        "expert_used": "gemini",
        "next_node": "tutor"
    }


async def tutor_node(state: TutorAgentState) -> Dict[str, Any]:
    """Placeholder — actual generation happens in run_agent_stream for streaming support."""
    return {"next_node": "memory"}


async def memory_node(state: TutorAgentState) -> Dict[str, Any]:
    """Saves learning progress, topic tags, and errors to Supabase profile records."""
    user_id = state["user_id"]
    subject = state["subject"]
    conv_id = state["conversation_id"]
    
    # 1. Create weakness snapshot
    from app.services.weakness_service import create_weakness_snapshot
    create_weakness_snapshot(user_id, subject)
    
    # 2. Check if we should update conversation summary (if chat thread is growing)
    messages = state["messages"]
    if len(messages) >= 8:
        print(f"[Agentic Memory] Evaluating conversation summary for {conv_id}...")
        api_key = settings.gemini_api_key
        if api_key:
            try:
                # Compile chat history text
                history_text = "\n".join(f"{type(m).__name__}: {m.content}" for m in messages[-10:])
                
                client = google_genai.Client(api_key=api_key)
                prompt = (
                    f"Chat history:\n{history_text}\n\n"
                    "Generate a concise, 1-sentence summary describing what concept the student is studying and "
                    "any specific difficulties or topics they struggled with (e.g. 'Student is practicing kinematics formulas and needs help with projectile motion vectors')."
                )
                response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
                if response and response.text:
                    summary = response.text.strip()
                    print(f"[Agentic Memory] Generated summary: {summary}")
                    
                    # Save summary in Redis cache
                    from app.services.redis_service import cache
                    cache.set(f"summary:{conv_id}", summary, expire_seconds=86400) # Cache for 1 day
                    
                    # Update conversation title in Supabase dynamically to reflect the topic summary
                    supabase.table('conversations').update({
                        'title': summary[:100]  # Cap title length
                    }).eq('id', conv_id).execute()
            except Exception as e:
                print(f"[Agentic Memory] Failed to generate summary: {e}")
                
    print(f"[Agentic Memory] Saved progress for user {user_id} in conv {conv_id}")
    return {"next_node": "end"}

# =====================================================================
# COMPILE LANGGRAPH
# =====================================================================

def build_tutor_graph():
    workflow = StateGraph(TutorAgentState)
    
    # Register Nodes
    workflow.add_node("router",         router_node)
    workflow.add_node("research",        research_node)
    workflow.add_node("visualizer",      visualizer_node)
    workflow.add_node("quiz",            quiz_node)
    workflow.add_node("roadmap",         roadmap_node)
    workflow.add_node("teach_back",      teach_back_node)
    workflow.add_node("subject_router",  subject_router_node)  # NEW
    workflow.add_node("expert",          expert_node)          # NEW
    workflow.add_node("tutor",           tutor_node)
    workflow.add_node("memory",          memory_node)
    
    # Entry
    workflow.set_entry_point("router")
    
    # Intent router → specialist or subject_router
    def route_from_router(state: TutorAgentState):
        return state["next_node"]
        
    workflow.add_conditional_edges(
        "router",
        route_from_router,
        {
            "research":      "research",
            "visualizer":    "visualizer",
            "quiz":          "quiz",
            "roadmap":       "roadmap",
            "teach_back":    "teach_back",
            "tutor":         "subject_router",   # tutor intent now goes through subject router first
        }
    )
    
    # Specialist nodes → subject_router (so they also get expert dispatch)
    # Exception: teach_back skips subject_router (purely conceptual evaluation)
    workflow.add_edge("research",     "subject_router")
    workflow.add_edge("visualizer",   "subject_router")
    workflow.add_edge("quiz",         "tutor")           # quiz keeps going direct to tutor
    workflow.add_edge("roadmap",      "tutor")           # roadmap keeps going direct to tutor
    workflow.add_edge("teach_back",   "tutor")           # teach_back keeps going direct to tutor
    workflow.add_edge("subject_router", "expert")
    workflow.add_edge("expert",       "tutor")
    workflow.add_edge("tutor",        "memory")
    workflow.add_edge("memory",       END)
    
    return workflow.compile()

# Compile singleton graph
tutor_graph = build_tutor_graph()

# =====================================================================
# STREAM RUNNER
# =====================================================================

async def run_agent_stream(
    conversation_id: str,
    user_id: str,
    message: str,
    subject: str,
    history: List[HistoryMessage]
):
    """
    Executes the TutorAI agent graph and yields streaming tokens/events.
    """
    # 1. Convert history to LangChain messages
    messages = []
    for msg in history:
        if msg.role == 'user':
            messages.append(HumanMessage(content=msg.content))
        else:
            messages.append(AIMessage(content=msg.content))
    messages.append(HumanMessage(content=message))
    
    # 2. Initial state
    initial_state = {
        "messages": messages,
        "subject": subject,
        "user_id": user_id,
        "conversation_id": conversation_id,
        "topic_tags": [],
        "weak_topics": [],
        "research_results": None,
        "visualization_data": None,
        "quiz_data": None,
        "suggested_videos": None,
        "roadmap_steps": None,
        "teach_back_data": None,
        "next_node": "router",
        # Expert routing fields
        "question_type": "ambiguous",
        "expert_result": None,
        "expert_used": "gemini",
    }
    
    # 3. Execute Graph Node-by-Node until we hit Tutor node
    state = initial_state
    
    # Execute router
    state.update(await router_node(state))
    next_step = state["next_node"]
    
    # Execute intermediate nodes
    if next_step == "research":
        state.update(await research_node(state))
        # Research results feed into subject_router + expert for numerical follow-ups
        state.update(await subject_router_node(state))
        state.update(await expert_node(state))
    elif next_step == "visualizer":
        state.update(await visualizer_node(state))
        state.update(await subject_router_node(state))
        state.update(await expert_node(state))
    elif next_step == "quiz":
        state.update(await quiz_node(state))          # quiz bypasses expert routing
    elif next_step == "roadmap":
        state.update(await roadmap_node(state))       # roadmap bypasses expert routing
    elif next_step == "teach_back":
        state.update(await teach_back_node(state))    # teach_back bypasses expert routing
    else:
        # Pure tutor intent → run subject router + expert
        state.update(await subject_router_node(state))
        state.update(await expert_node(state))
        
    # 4. Stream response from Tutor Node
    # Build prompt prefix with helper insights from tools and cached student profiles
    from app.services.redis_service import cache
    from app.services.weakness_service import get_top_weak_topics
    
    context_prefix = ""
    
    # Inject cached conversation summary if exists
    cached_summary = cache.get(f"summary:{conversation_id}")
    if cached_summary:
        context_prefix += f"\n\n[Active Conversation Summary Context]:\n{cached_summary}\n"
        
    # Inject student profile weakness info
    cached_weakness = cache.get(f"weakness:{user_id}:{subject}")
    if not cached_weakness:
        cached_weakness = get_top_weak_topics(user_id, subject, n=2)
    if cached_weakness:
        context_prefix += f"\n\n[Student Weak Topics in {subject.capitalize()}]:\n{', '.join(cached_weakness)}\n"
        
    if state.get("research_results"):
        context_prefix += f"\n\n[Research Grounding Info]:\n{state['research_results']}\n"
    if state.get("suggested_videos"):
        context_prefix += f"\n\n[YouTube Recommendations]:\n{state['suggested_videos']}\n"
    if state.get("visualization_data"):
        context_prefix += f"\n\n[Visualization Engine loaded plot data for expression '{state['visualization_data']['expression']}']\n"
    if state.get("quiz_data"):
        q = state["quiz_data"]
        context_prefix += f"\n\n[Quiz Challenge Alert]:\nQuestion: {q['question']}\nOptions: {', '.join(q['options'])}\n"
    if state.get("roadmap_steps"):
        steps = state["roadmap_steps"]
        roadmap_md = "\n".join(
            f"- [{'x' if s['status']=='completed' else '/' if s['status']=='in-progress' else ' '}] {s['topic']}"
            for s in steps
        )
        context_prefix += f"\n\n[Active Learning Roadmap Progress]:\n{roadmap_md}\n"
    if state.get("teach_back_data"):
        tb = state["teach_back_data"]
        context_prefix += (
            f"\n\n[Teach-Back Evaluation Results]:\n"
            f"Score: {tb['score']}\n"
            f"Coverage: {', '.join(tb['coverage'])}\n"
            f"Missing: {', '.join(tb['missing_concepts'])}\n"
            f"Misconceptions: {', '.join(tb['misconceptions'])}\n"
            f"Feedback: {tb['feedback']}\n"
        )
        
    # User message with context injected
    augmented_message = message
    if context_prefix:
        augmented_message = f"{context_prefix}\n---\nUser query: {message}"
        
    # Yield initial loading notice for client if we ran tools
    if next_step != "tutor":
        yield f"*(TutorAI {next_step.capitalize()} Agent active... processing results)*\\n\\n"

    # ── Expert dispatch ──────────────────────────────────────────────────────
    # If expert_node already ran LoRA and got a high-confidence answer, use it
    # as raw_answer for Gemini formatter. Otherwise call generate_answer() as before.
    expert_result = state.get("expert_result")
    expert_used   = state.get("expert_used", "gemini")

    loop = asyncio.get_running_loop()

    if expert_result and expert_result.get("confidence", 0) >= CONFIDENCE_THRESHOLD:
        # LoRA answered — use its output; skip the generate_answer() LoRA call
        raw_answer = expert_result["answer"]
        reasoning  = expert_result.get("reasoning_steps", "")
        boxed      = expert_result.get("final_result", "")
        yield f"*(🔬 {expert_used.replace('_', ' ').title()} Expert active...)*\\n\\n"

        from app.services.llm_service import extract_topic_tags
        topic_tags = extract_topic_tags(message, raw_answer)

        # Append structured breakdown before Gemini formats it
        if reasoning:
            raw_answer = f"<think>\n{reasoning}\n</think>\n\n{raw_answer}"
    else:
        # Gemini path — call generate_answer() which does its own adapter swap
        yield "*(Thinking...)*\\n\\n"
        ai_result  = await loop.run_in_executor(
            None, generate_answer, augmented_message, history, subject
        )
        raw_answer = ai_result.get("answer", "")
        topic_tags = ai_result.get("topic_tags", [])
    
    # If we have teach-back data, append the concept name to topic_tags
    if state.get("teach_back_data"):
        tb = state["teach_back_data"]
        concept = tb.get("concept")
        if concept:
            concept_clean = concept.strip()
            if concept_clean and concept_clean not in topic_tags:
                topic_tags.append(concept_clean)
            if concept_clean.lower() not in topic_tags:
                topic_tags.append(concept_clean.lower())
    
    # Stream the final formatted output via Gemini
    full_response = ""
    for chunk in generate_answer_stream(augmented_message, history, subject, raw_answer):
        full_response += chunk
        yield chunk
        
    # If we have a visualization data generated, render the custom code blocks
    if state.get("visualization_data"):
        viz = state["visualization_data"]
        viz_type = viz.get("type")
        
        if viz_type == "function_plot":
            viz_markdown = (
                f"\n\n### 📊 Mathematical Function Plot\n"
                f"*(Generating interactive curve grid for expression: `{viz.get('expression')}`)*\n"
                f"```visualizer_chart\n"
                f"{json.dumps(viz)}\n"
                f"```\n"
            )
            yield viz_markdown
            full_response += viz_markdown
            
        elif viz_type == "flowchart":
            viz_markdown = (
                f"\n\n### 🗺️ Concept Map: {viz.get('title', 'Diagram')}\n"
                f"*(Rendering interactive structural map)*\n"
                f"```visualizer_flow\n"
                f"{json.dumps(viz)}\n"
                f"```\n"
            )
            yield viz_markdown
            full_response += viz_markdown
            
        elif viz_type == "dp_table":
            viz_markdown = (
                f"\n\n### 📝 Step-by-Step DP Table: {viz.get('problem', 'Knapsack')}\n"
                f"*(Interactive calculation grid loaded successfully)*\n"
                f"```visualizer_dp\n"
                f"{json.dumps(viz)}\n"
                f"```\n"
            )
            yield viz_markdown
            full_response += viz_markdown

    # If we have a quiz generated, render it beautifully
    if state.get("quiz_data"):
        q = state["quiz_data"]
        quiz_markdown = f"\n\n### 📝 Concept Check\n**{q['question']}**\n"
        for idx, opt in enumerate(q["options"]):
            letter = chr(65 + idx)
            quiz_markdown += f"- **{letter})** {opt}\n"
        yield quiz_markdown
        full_response += quiz_markdown
        
    # If we have a roadmap loaded, render it beautifully
    if state.get("roadmap_steps"):
        steps = state["roadmap_steps"]
        roadmap_md = f"\n\n### 🗺️ Your {subject.capitalize()} Study Roadmap\n"
        for s in steps:
            status_icon = "✅" if s["status"] == "completed" else "⚡" if s["status"] == "in-progress" else "🔒"
            roadmap_md += f"- **{status_icon} {s['topic']}**\n"
        yield roadmap_md
        full_response += roadmap_md
        
    # If we have a teach-back scorecard, render it beautifully
    if state.get("teach_back_data"):
        tb = state["teach_back_data"]
        coverage_bullets = "\n".join(f"  - {c}" for c in tb.get("coverage", [])) if tb.get("coverage") else "  - None identified."
        missing_bullets = "\n".join(f"  - {m}" for m in tb.get("missing_concepts", [])) if tb.get("missing_concepts") else "  - No missing concepts! Great job."
        misconception_bullets = "\n".join(f"  - {mis}" for mis in tb.get("misconceptions", [])) if tb.get("misconceptions") else "  - None detected! Excellent conceptual clarity."
        
        scorecard = (
            f"\n\n### 🎓 Teach-Back Scorecard\n\n"
            f"> **Concept:** *{tb.get('concept', subject.capitalize())}*\n\n"
            f"| Metric | Rating |\n"
            f"| :--- | :--- |\n"
            f"| **Active Recall Score** | **`{tb['score']}/100`** |\n"
            f"| **Explanation Confidence** | `{tb['confidence']}` |\n\n"
            f"#### 🔍 Explanation Breakdown\n"
            f"* **✅ Concept Coverage:**\n{coverage_bullets}\n"
            f"* **❌ Missing Points:**\n{missing_bullets}\n"
            f"* **⚠️ Misconceptions Detected:**\n{misconception_bullets}\n\n"
            f"> [!TIP]\n"
            f"> **IIT-JEE Tutor Feedback:**\n"
            f"> {tb['feedback']}\n"
        )
        yield scorecard
        full_response += scorecard
        
        # Determine is_correct for database flagging
        has_misconceptions = False
        if tb.get("misconceptions"):
            filtered_misconceptions = [m for m in tb["misconceptions"] if m.strip().lower() not in ["none", "none detected", "none detected!", "no misconceptions", "none detected! excellent conceptual clarity."]]
            if filtered_misconceptions:
                has_misconceptions = True
                
        if tb["score"] < 70 or has_misconceptions:
            print(f"[Teach-Back] Misconception flagged. Updating user message is_correct = False")
            try:
                user_res = supabase.table('messages').select('id').eq('conversation_id', conversation_id).eq('role', 'user').order('created_at', desc=True).limit(1).execute()
                if user_res.data:
                    msg_id = user_res.data[0]['id']
                    supabase.table('messages').update({'is_correct': False}).eq('id', msg_id).execute()
            except Exception as e:
                print(f"[Teach-Back] Failed to update user message correct status: {e}")
                
    # At the end of standard conceptual tutor generation, invite teach-back check
    if next_step == "tutor" and not state.get("teach_back_data") and not state.get("quiz_data") and not state.get("roadmap_steps"):
        invitation = (
            "\n\n---\n"
            "💡 *Would you like to explain this concept back to me in your own words to check your understanding?* "
            "Just reply with your interpretation to test your active recall!"
        )
        yield invitation
        full_response += invitation
        
    # 5. Save output to Supabase & trigger Memory update
    is_correct_val = None
    if state.get("teach_back_data"):
        tb = state["teach_back_data"]
        has_misconceptions = False
        if tb.get("misconceptions"):
            filtered_misconceptions = [m for m in tb["misconceptions"] if m.strip().lower() not in ["none", "none detected", "none detected!", "no misconceptions"]]
            if filtered_misconceptions:
                has_misconceptions = True
        if tb.get("score", 100) < 70 or has_misconceptions:
            is_correct_val = False
        else:
            is_correct_val = True

    save_assistant_message(
        conversation_id=conversation_id,
        user_id=user_id,
        content=full_response,
        topic_tags=topic_tags,
        is_correct=is_correct_val
    )
    
    # Update memory node asynchronously
    state["topic_tags"] = topic_tags
    await memory_node(state)
