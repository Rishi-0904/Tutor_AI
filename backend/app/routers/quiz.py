from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from app.models.schemas import UserInfo, QuizGenerateRequest, QuizSubmitRequest, QuizSubmitResponse
from app.middleware.auth import get_current_user
from app.core.supabase_client import supabase
from app.services.quiz_service import generate_adaptive_quiz
from datetime import datetime

router = APIRouter(prefix="/quiz", tags=["quiz"])

@router.post("/generate")
async def generate_quiz_endpoint(req: QuizGenerateRequest, user: UserInfo = Depends(get_current_user)):
    quiz_data = generate_adaptive_quiz(
        user_id=user.id,
        subject=req.subject,
        num_questions=req.numQuestions,
        manual_difficulty=req.difficulty
    )
    
    questions = quiz_data.get("questions", [])
    difficulty = quiz_data.get("difficulty", "medium")
    weak_topics = quiz_data.get("weak_topics", [])
    
    if not questions:
        raise HTTPException(status_code=500, detail="Failed to load questions from dataset")

    # Default to 2 minutes per question if no time limit is provided
    time_limit = req.timeLimit or (len(questions) * 2)
    
    res = supabase.table('quiz_attempts').insert({
        'user_id': user.id,
        'subject': req.subject,
        'weak_topics': weak_topics,
        'questions': questions,
        'total': len(questions)
    }).execute()
    
    attempt = res.data[0]
    return {
        "id": attempt["id"],
        "subject": req.subject,
        "weakTopics": weak_topics,
        "difficulty": difficulty,
        "questions": questions,
        "timeLimit": time_limit
    }

@router.post("/submit", response_model=QuizSubmitResponse)
async def submit_quiz(req: QuizSubmitRequest, user: UserInfo = Depends(get_current_user)):
    attempt_res = supabase.table('quiz_attempts').select('*').eq('id', req.quizId).eq('user_id', user.id).execute()
    if not attempt_res.data:
        raise HTTPException(status_code=404, detail="Quiz not found")
        
    attempt = attempt_res.data[0]
    if attempt.get("completed_at"):
        raise HTTPException(status_code=400, detail="Quiz already submitted")
        
    questions = attempt.get("questions", [])
    score = 0
    detailed_responses = []
    
    for q in questions:
        q_id = str(q["id"])
        selected = req.responses.get(q_id)
        is_correct = selected == q["correct_answer"]
        if is_correct:
            score += 1
        detailed_responses.append({
            "question_id": q_id,
            "selected": selected,
            "is_correct": is_correct
        })
        
    update_res = supabase.table('quiz_attempts').update({
        'responses': detailed_responses,
        'score': score,
        'completed_at': datetime.utcnow().isoformat()
    }).eq('id', req.quizId).execute()
    
    return QuizSubmitResponse(
        score=score,
        total=attempt.get("total", 5),
        responses=detailed_responses
    )

@router.get("/history")
async def get_quiz_history(user: UserInfo = Depends(get_current_user)):
    res = supabase.table('quiz_attempts') \
        .select('id, subject, weak_topics, score, total, completed_at, created_at') \
        .eq('user_id', user.id) \
        .order('created_at', desc=True) \
        .execute()
    return res.data
