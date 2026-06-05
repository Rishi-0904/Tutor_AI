import os
import re
import html
import json
import ast
import pandas as pd
from typing import Dict, Any, List, Optional
from app.core.supabase_client import supabase
from app.services.weakness_service import get_top_weak_topics
from app.core.config import settings
from google import genai as google_genai
from google.genai import types

# Lazy-loaded dataframe
_jee_df = None

def load_jee_dataset() -> Optional[pd.DataFrame]:
    """Helper to lazily load the JEE dataset from workspace."""
    global _jee_df
    if _jee_df is not None:
        return _jee_df
        
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    project_root = os.path.dirname(base_dir)
    csv_path = os.path.join(project_root, "preprocessing", "jee_data_all.csv")
    
    try:
        if os.path.exists(csv_path):
            print(f"[Quiz Service] Loading JEE dataset from {csv_path}...")
            df = pd.read_csv(csv_path, usecols=[
                'question_id', 'subject', 'chapter', 'topic', 
                'question', 'options', 'correct_option', 
                'explanation', 'question_type'
            ])
            _jee_df = df[df['question_type'] == 'mcq']
            return _jee_df
    except Exception as e:
        print(f"[Quiz Service] Failed to load dataset: {e}")
    return None

def clean_latex_string(text: str) -> str:
    """Cleans up formatting issues, tags, and escapes inside LaTeX expressions."""
    if not isinstance(text, str):
        return ""
    # Replace HTML linebreaks
    text = re.sub(r'<br\s*/?>', '\n', text)
    # Unescape HTML entities
    text = html.unescape(text)
    # Strip double slashes sometimes introduced by CSV parses
    text = text.replace('\\\\', '\\')
    return text.strip()

# =====================================================================
# ADAPTIVE CAPABILITY EVALUATION
# =====================================================================

def evaluate_student_difficulty(user_id: str, subject: str) -> str:
    """
    Queries the last 3 completed quiz attempts for the student.
    Determines capability:
    - Average score > 80% ➔ Hard
    - Average score < 50% ➔ Easy
    - Default/Otherwise ➔ Medium
    """
    try:
        res = supabase.table('quiz_attempts') \
            .select('score, total') \
            .eq('user_id', user_id) \
            .eq('subject', subject) \
            .not_.is_('completed_at', 'null') \
            .order('completed_at', desc=True) \
            .limit(3) \
            .execute()
            
        attempts = res.data or []
        if not attempts:
            return "medium"
            
        total_score = 0
        total_questions = 0
        for att in attempts:
            total_score += att.get('score', 0)
            total_questions += att.get('total', 5)
            
        if total_questions == 0:
            return "medium"
            
        rate = total_score / total_questions
        print(f"[Quiz Service] Evaluated historical score rate for {user_id} on {subject}: {rate:.2f}")
        
        if rate >= 0.8:
            return "hard"
        elif rate < 0.5:
            return "easy"
        return "medium"
    except Exception as e:
        print(f"[Quiz Service] Error evaluating difficulty: {e}")
        return "medium"

# =====================================================================
# QUESTION SOURCING & GENERATION
# =====================================================================

def generate_adaptive_quiz(
    user_id: str, 
    subject: str, 
    num_questions: int = 5, 
    manual_difficulty: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generates an adaptive quiz:
    1. Evaluates target difficulty level.
    2. Sources questions matching student weak topics from the dataset.
    3. Falls back to Gemini-assisted generation if dataset matches are insufficient.
    """
    subject = subject.lower()
    difficulty = manual_difficulty or evaluate_student_difficulty(user_id, subject)
    weak_topics = get_top_weak_topics(user_id, subject, n=3)
    
    print(f"[Quiz Service] Sourcing adaptive quiz: difficulty={difficulty}, weak_topics={weak_topics}")
    
    questions = []
    
    # 1. Attempt Sourcing from Local CSV Dataset
    df = load_jee_dataset()
    if df is not None:
        try:
            # Filter by subject
            subj_filter = df[df['subject'].str.lower() == subject]
            
            # Filter by weak topics
            weak_topics_lower = [t.lower() for t in weak_topics]
            topic_filter = subj_filter[subj_filter['topic'].str.lower().isin(weak_topics_lower)]
            
            # If we don't have enough specific topic matches, expand search to the chapter level
            if len(topic_filter) < num_questions:
                topic_filter = subj_filter
                
            sampled_df = topic_filter.sample(n=min(num_questions, len(topic_filter)))
            
            for _, row in sampled_df.iterrows():
                try:
                    # Parse Options
                    opts = row['options']
                    try:
                        options_raw = json.loads(opts)
                    except:
                        options_raw = ast.literal_eval(opts)
                    parsed_options = [clean_latex_string(opt['content']) for opt in options_raw]
                    
                    # Parse Correct Option
                    corr = row['correct_option']
                    try:
                        correct_raw = json.loads(corr)[0]
                    except:
                        try:
                            correct_raw = ast.literal_eval(corr)[0]
                        except:
                            correct_raw = str(corr).strip("[]'\"")
                            
                    questions.append({
                        "id": row['question_id'],
                        "subject": row['subject'],
                        "chapter": row['chapter'],
                        "topic": row['topic'],
                        "question": clean_latex_string(str(row['question'])),
                        "options": parsed_options,
                        "correct_answer": correct_raw, # A, B, C, D
                        "explanation": clean_latex_string(str(row['explanation'])) if pd.notna(row['explanation']) else "",
                        "difficulty": difficulty
                    })
                except:
                    continue
        except Exception as e:
            print(f"[Quiz Service] Local dataset parsing error: {e}")

    # 2. LLM Fallback Generation if we need more questions
    num_needed = num_questions - len(questions)
    if num_needed > 0 and settings.gemini_api_key:
        print(f"[Quiz Service] Sourcing {num_needed} additional questions via Gemini fallback...")
        try:
            topics_str = ", ".join(weak_topics) if weak_topics else subject
            client = google_genai.Client(api_key=settings.gemini_api_key)
            
            prompt = f"""Generate exactly {num_needed} IIT-JEE level multiple choice questions on {subject} topic(s): {topics_str}.
Target difficulty: {difficulty.upper()} (EASY = direct conceptual formulas, MEDIUM = JEE Main level, HARD = JEE Advanced multi-step problems).
Return ONLY a valid JSON object matching this schema:
{{
  "questions": [
    {{
      "id": "gen_{subject}_01",
      "subject": "{subject}",
      "chapter": "Chapter Name",
      "topic": "Topic Name",
      "question": "The question content (use LaTeX formatting for math expressions, e.g. $$y = x^2$$ or $x$)",
      "options": ["Option A text", "Option B text", "Option C text", "Option D text"],
      "correct_answer": "A",
      "explanation": "Brief step-by-step resolution explanation"
    }}
  ]
}}
"""
            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            
            if response and response.text:
                generated = json.loads(response.text.strip())
                for q in generated.get("questions", []):
                    # Inject difficulty tag
                    q["difficulty"] = difficulty
                    questions.append(q)
        except Exception as e:
            print(f"[Quiz Service] LLM Fallback generation failed: {e}")
            
    # Truncate to desired size
    questions = questions[:num_questions]
    
    # 3. Last Resort Standalone Fallback if everything fails
    if not questions:
        questions = [{
            "id": "fallback_01",
            "subject": subject,
            "chapter": "General",
            "topic": "Basics",
            "question": f"Conceptual check: Solve for the base equations in {subject.capitalize()}.",
            "options": ["Choice A", "Choice B", "Choice C", "Choice D"],
            "correct_answer": "A",
            "explanation": "No custom explanation available.",
            "difficulty": difficulty
        }]
        
    return {
        "difficulty": difficulty,
        "weak_topics": weak_topics,
        "questions": questions
    }
