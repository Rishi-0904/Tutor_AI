import sys
import os
import json
from typing import Dict, Any, List, Optional

# Add backend directory to sys.path for direct imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from mcp.server.fastmcp import FastMCP
from app.core.supabase_client import supabase
from app.core.config import settings
from google import genai as google_genai

# Initialize FastMCP Server
mcp = FastMCP("TutorAI-MCP")

# =====================================================================
# TOOL: Student Profile Tracking
# =====================================================================

@mcp.tool()
def get_student_profile(user_id: str) -> Dict[str, Any]:
    """
    Fetches the profile details and topic masteries for a student.
    """
    print(f"[Profile MCP] Fetching profile for user {user_id}")
    try:
        # Fetch profile
        prof_res = supabase.table('profiles').select('*').eq('id', user_id).execute()
        profile = prof_res.data[0] if prof_res.data else {}
        
        # Fetch masteries
        mastery_res = supabase.table('topic_mastery').select('topic, score, updated_at').eq('user_id', user_id).execute()
        masteries = mastery_res.data or []
        
        return {
            "profile": {
                "id": user_id,
                "full_name": profile.get("full_name"),
                "username": profile.get("username"),
                "grade": profile.get("grade"),
                "current_goal": profile.get("current_goal", "JEE Advanced 2027")
            },
            "topic_mastery": masteries
        }
    except Exception as e:
        return {"error": f"Failed to retrieve student profile: {e}"}

@mcp.tool()
def update_mastery_score(user_id: str, topic: str, score: int) -> Dict[str, Any]:
    """
    Updates the student's mastery score for a specific physics/chem/math topic.
    Score should be an integer from 0 to 100.
    """
    print(f"[Profile MCP] Updating mastery for {user_id} - Topic: {topic}, Score: {score}")
    try:
        topic_clean = topic.strip().lower()
        res = supabase.table('topic_mastery').upsert({
            'user_id': user_id,
            'topic': topic_clean,
            'score': min(max(0, score), 100),
            'updated_at': 'now()'
        }, on_conflict='user_id,topic').execute()
        
        return {
            "success": True,
            "message": f"Updated mastery for topic '{topic_clean}' to {score}%",
            "data": res.data[0] if res.data else {}
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to update mastery score: {e}"}

@mcp.tool()
def get_weak_topics(user_id: str) -> List[str]:
    """
    Retrieves a list of weak topics (mastery score < 60) for a student.
    """
    print(f"[Profile MCP] Fetching weak topics for user {user_id}")
    try:
        res = supabase.table('topic_mastery').select('topic').eq('user_id', user_id).lt('score', 60).execute()
        if res.data:
            return [row['topic'] for row in res.data]
        return []
    except Exception as e:
        print(f"[Profile MCP] Error in get_weak_topics: {e}")
        return []

# =====================================================================
# TOOL: Learning Context Aggregator
# =====================================================================

@mcp.tool()
def get_learning_context(user_id: str) -> Dict[str, Any]:
    """
    Generates a unified learning context report for a user, containing goals,
    weak topics, strong topics, recent focus topics, and recent test performance.
    """
    print(f"[Profile MCP] Generating learning context for user {user_id}")
    try:
        # 1. Fetch profile & goal
        prof_res = supabase.table('profiles').select('current_goal').eq('id', user_id).execute()
        goal = prof_res.data[0].get('current_goal', 'JEE Advanced 2027') if prof_res.data else 'JEE Advanced 2027'
        
        # 2. Fetch masteries
        mastery_res = supabase.table('topic_mastery').select('topic, score').eq('user_id', user_id).execute()
        masteries = mastery_res.data or []
        
        weak_topics = [m['topic'] for m in masteries if m['score'] < 60]
        strong_topics = [m['topic'] for m in masteries if m['score'] >= 80]
        
        # 3. Fetch recent topics from messages table
        recent_topics = []
        msg_res = supabase.table('messages').select('topic_tags').eq('user_id', user_id).order('created_at', desc=True).limit(10).execute()
        if msg_res.data:
            seen = set()
            for row in msg_res.data:
                tags = row.get('topic_tags') or []
                for t in tags:
                    t_lower = t.strip().lower()
                    if t_lower and t_lower not in seen:
                        seen.add(t_lower)
                        recent_topics.append(t)
        
        # 4. Fetch recent test scores from quiz_attempts
        quiz_res = supabase.table('quiz_attempts').select('subject, score, total, completed_at') \
            .eq('user_id', user_id).not_.is_('completed_at', 'null') \
            .order('created_at', desc=True).limit(3).execute()
        recent_tests = quiz_res.data or []
        
        return {
            "goal": goal,
            "weak_topics": weak_topics,
            "strong_topics": strong_topics,
            "recent_topics": recent_topics[:4],
            "recent_tests": recent_tests
        }
    except Exception as e:
        return {"error": f"Failed to load learning context: {e}"}

# =====================================================================
# TOOL: Vector PDF Textbook & Note Search
# =====================================================================

@mcp.tool()
def search_pdf(query: str, user_id: str) -> Dict[str, Any]:
    """
    Performs a semantic vector search across the student's uploaded PDF documents.
    Generates embedding coordinates dynamically using Gemini.
    """
    print(f"[PDF MCP] Querying notes vector index for user {user_id}: '{query}'")
    api_key = settings.gemini_api_key
    if not api_key:
        return {"error": "Gemini API key not configured on server"}
        
    try:
        # Generate query embedding vector
        client = google_genai.Client(api_key=api_key)
        emb_res = client.models.embed_content(
            model="text-embedding-004",
            contents=query
        )
        query_embedding = emb_res.embeddings[0].values
        
        # Run similarity RPC query in Supabase
        rpc_res = supabase.rpc('match_pdf_chunks', {
            'query_embedding': query_embedding,
            'match_threshold': 0.35, # Cosine similarity cutoff
            'match_count': 3,
            'p_user_id': user_id
        }).execute()
        
        chunks = rpc_res.data or []
        if not chunks:
            return {"results": "No relevant notes or paragraphs found matching this description."}
            
        formatted_results = []
        for i, chk in enumerate(chunks):
            formatted_results.append(f"--- MATCH {i+1} (Similarity: {round(chk.get('similarity', 0)*100, 1)}%) ---\n{chk['content']}")
            
        return {"results": "\n\n".join(formatted_results)}
    except Exception as e:
        return {"error": f"Failed to execute semantic vector search: {e}"}

# =====================================================================
# TOOL: Whiteboard Sketches
# =====================================================================

@mcp.tool()
def save_sketch(user_id: str, conversation_id: str, title: str, svg_data: str) -> Dict[str, Any]:
    """
    Saves a whiteboard vector sketch to the active conversation history.
    """
    print(f"[Whiteboard MCP] Saving sketch '{title}' for user {user_id}")
    try:
        res = supabase.table('whiteboard_sketches').insert({
            'user_id': user_id,
            'conversation_id': conversation_id,
            'title': title,
            'svg_data': svg_data
        }).execute()
        
        return {
            "success": True,
            "message": f"Sketch '{title}' saved successfully.",
            "data": res.data[0] if res.data else {}
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to save sketch: {e}"}

@mcp.tool()
def load_sketches(user_id: str, conversation_id: str) -> List[Dict[str, Any]]:
    """
    Loads all whiteboard sketches for a specific conversation thread.
    """
    print(f"[Whiteboard MCP] Loading sketches for conv {conversation_id}")
    try:
        res = supabase.table('whiteboard_sketches').select('*') \
            .eq('user_id', user_id).eq('conversation_id', conversation_id) \
            .order('created_at', desc=True).execute()
        return res.data or []
    except Exception as e:
        print(f"[Whiteboard MCP] Error loading sketches: {e}")
        return []

if __name__ == "__main__":
    # Start the FastMCP stdio server loop
    mcp.run()
