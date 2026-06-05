import json
from typing import Dict, Any, List, Optional
from app.core.supabase_client import supabase
from app.services.redis_service import cache

# =====================================================================
# JEE TOPIC DEPENDENCY GRAPHS
# =====================================================================

DEFAULT_ROADMAPS = {
    "physics": [
        {"topic": "Basic Mathematics", "prerequisites": [], "status": "in-progress"},
        {"topic": "Kinematics", "prerequisites": ["Basic Mathematics"], "status": "locked"},
        {"topic": "Laws of Motion", "prerequisites": ["Kinematics"], "status": "locked"},
        {"topic": "Work, Power, Energy", "prerequisites": ["Laws of Motion"], "status": "locked"},
        {"topic": "Rotational Mechanics", "prerequisites": ["Work, Power, Energy"], "status": "locked"},
        {"topic": "Gravitation", "prerequisites": ["Laws of Motion"], "status": "locked"},
        {"topic": "Electrostatics", "prerequisites": ["Gravitation", "Work, Power, Energy"], "status": "locked"},
    ],
    "mathematics": [
        {"topic": "Sets & Relations", "prerequisites": [], "status": "in-progress"},
        {"topic": "Quadratic Equations", "prerequisites": [], "status": "in-progress"},
        {"topic": "Complex Numbers", "prerequisites": ["Quadratic Equations"], "status": "locked"},
        {"topic": "Limits & Continuity", "prerequisites": ["Sets & Relations"], "status": "locked"},
        {"topic": "Differentiation", "prerequisites": ["Limits & Continuity"], "status": "locked"},
        {"topic": "Integration", "prerequisites": ["Differentiation"], "status": "locked"},
        {"topic": "Differential Equations", "prerequisites": ["Integration"], "status": "locked"},
    ],
    "chemistry": [
        {"topic": "Atomic Structure", "prerequisites": [], "status": "in-progress"},
        {"topic": "Chemical Bonding", "prerequisites": ["Atomic Structure"], "status": "locked"},
        {"topic": "Mole Concept", "prerequisites": [], "status": "in-progress"},
        {"topic": "Chemical Equilibrium", "prerequisites": ["Mole Concept"], "status": "locked"},
        {"topic": "Organic Chemistry Basics", "prerequisites": ["Chemical Bonding"], "status": "locked"},
        {"topic": "Isomerism", "prerequisites": ["Organic Chemistry Basics"], "status": "locked"},
        {"topic": "Hydrocarbons", "prerequisites": ["Isomerism"], "status": "locked"},
    ]
}

# =====================================================================
# ROADMAP SERVICE OPERATIONS
# =====================================================================

def get_or_create_roadmap(user_id: str, subject: str) -> List[Dict[str, Any]]:
    """
    Retrieves the roadmap for a user/subject.
    If not found, initializes a default roadmap from dependencies and saves it.
    """
    subject = subject.lower()
    if subject not in DEFAULT_ROADMAPS:
        subject = "physics" # fallback
        
    cache_key = f"roadmap:{user_id}:{subject}"
    
    # 1. Try reading from cache
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data
        
    # 2. Query Supabase
    try:
        res = supabase.table('roadmaps').select('*').eq('user_id', user_id).eq('subject', subject).execute()
        if res.data:
            steps = res.data[0]['steps']
            cache.set(cache_key, steps, expire_seconds=86400) # Cache for 1 day
            return steps
            
        # 3. Create default roadmap if missing
        default_steps = DEFAULT_ROADMAPS[subject]
        insert_res = supabase.table('roadmaps').insert({
            'user_id': user_id,
            'subject': subject,
            'steps': default_steps
        }).execute()
        
        steps = insert_res.data[0]['steps'] if insert_res.data else default_steps
        cache.set(cache_key, steps, expire_seconds=86400)
        return steps
    except Exception as e:
        print(f"[Roadmap Service] Error getting/creating roadmap: {e}")
        return DEFAULT_ROADMAPS[subject]

def update_roadmap_topic_status(user_id: str, subject: str, topic_name: str, new_status: str) -> List[Dict[str, Any]]:
    """
    Updates the status of a specific topic in the user's roadmap.
    If the topic is completed, automatically unlocks downstream topics (changing status 
    from 'locked' to 'in-progress') if all their prerequisites are satisfied.
    Allows students to freely jump around (e.g. they can mark anything as completed).
    """
    subject = subject.lower()
    valid_statuses = ["locked", "in-progress", "completed"]
    if new_status not in valid_statuses:
        print(f"[Roadmap Service] Invalid status: {new_status}")
        return []
        
    steps = get_or_create_roadmap(user_id, subject)
    
    # 1. Update status of target topic
    target_found = False
    for step in steps:
        if step["topic"].lower() == topic_name.lower():
            step["status"] = new_status
            target_found = True
            break
            
    if not target_found:
        print(f"[Roadmap Service] Topic '{topic_name}' not found in {subject} roadmap.")
        return steps
        
    # 2. Evaluate downstream unlocks if target was marked completed
    if new_status == "completed":
        completed_topics = {s["topic"].lower() for s in steps if s["status"] == "completed"}
        for step in steps:
            if step["status"] == "locked":
                # Unlock if all prerequisites are now satisfied
                prereqs = [p.lower() for p in step["prerequisites"]]
                if prereqs and all(p in completed_topics for p in prereqs):
                    step["status"] = "in-progress"
                    print(f"[Roadmap Service] Auto-unlocked topic: '{step['topic']}'")
                    
    # 3. Update Supabase
    try:
        supabase.table('roadmaps').update({'steps': steps}).eq('user_id', user_id).eq('subject', subject).execute()
        
        # 4. Refresh cache
        cache_key = f"roadmap:{user_id}:{subject}"
        cache.set(cache_key, steps, expire_seconds=86400)
    except Exception as e:
        print(f"[Roadmap Service] Error updating database: {e}")
        
    return steps
