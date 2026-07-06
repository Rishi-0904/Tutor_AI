import json
from typing import Dict, Any, List
from app.core.config import settings
from google import genai as google_genai
from google.genai import types

def evaluate_student_explanation(concept: str, explanation: str) -> Dict[str, Any]:
    """
    Evaluates the student's concept explanation using Gemini.
    Returns a dictionary containing explanation score, coverage points,
    missing concepts, misconceptions, confidence rating, and feedback.
    """
    fallback_response = {
        "score": 50,
        "coverage": [],
        "missing_concepts": [],
        "misconceptions": ["Unable to run evaluation due to configuration issues."],
        "confidence": "Medium",
        "feedback": "Evaluation service is currently offline. Please check back later."
    }
    
    api_key = settings.gemini_api_key
    if not api_key:
        print("[Teach-Back] Gemini API key missing. Returning fallback response.")
        return fallback_response
        
    print(f"[Teach-Back] Evaluating explanation for concept '{concept}'...")
    
    try:
        client = google_genai.Client(api_key=api_key)
        
        prompt = f"""You are an expert IIT-JEE tutor. Evaluate the student's explanation of the concept: "{concept}".
Student Explanation:
"{explanation}"

Analyze the explanation for:
1. Score: Rate their overall explanation quality from 0 to 100.
2. Coverage: Core ideas they correctly mentioned.
3. Missing Concepts: Key facts or principles they forgot to state.
4. Misconceptions: Any scientifically incorrect details or faulty logic.
5. Confidence: Rate their explanation confidence level (HIGH, MEDIUM, or LOW).
6. Feedback: Direct, constructive tutoring comments correcting any misconceptions.

Return ONLY a valid JSON object matching this schema:
{{
  "score": 85,
  "coverage": ["..."],
  "missing_concepts": ["..."],
  "misconceptions": ["..."],
  "confidence": "HIGH",
  "feedback": "..."
}}
"""
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        
        if response and response.text:
            parsed = json.loads(response.text.strip())
            print(f"[Teach-Back] Evaluation complete. Score: {parsed.get('score', 0)}")
            return parsed
            
    except Exception as e:
        print(f"[Teach-Back] Error during evaluation: {e}")
        
    return fallback_response
