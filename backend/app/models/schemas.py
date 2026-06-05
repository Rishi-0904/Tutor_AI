from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class UserInfo(BaseModel):
    id: str
    email: str

class ProfileUpdate(BaseModel):
    username: Optional[str] = None
    full_name: Optional[str] = None
    grade: Optional[str] = None

class ConversationCreate(BaseModel):
    subject: str = "general"
    title: Optional[str] = None

class ChatRequest(BaseModel):
    conversationId: str
    content: str = ""
    # image_file is handled as Form data in the endpoint, so we don't need it here.

class ChatResponse(BaseModel):
    userMessage: dict
    aiMessage: dict

class QuizGenerateRequest(BaseModel):
    subject: str = "physics"
    numQuestions: int = 5
    timeLimit: Optional[int] = None # in minutes
    difficulty: Optional[str] = None # 'easy' | 'medium' | 'hard'

class QuizSubmitRequest(BaseModel):
    quizId: str
    responses: Dict[str, str]

class QuizSubmitResponse(BaseModel):
    score: int
    total: int
    responses: List[Dict[str, Any]]
