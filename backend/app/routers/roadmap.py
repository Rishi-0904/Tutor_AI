from fastapi import APIRouter, Depends, HTTPException
from app.middleware.auth import get_current_user
from app.models.schemas import UserInfo
from app.services.roadmap_service import get_or_create_roadmap, update_roadmap_topic_status
from pydantic import BaseModel

router = APIRouter(prefix="/roadmap", tags=["roadmap"])

class RoadmapUpdate(BaseModel):
    subject: str
    topic: str
    status: str

@router.get("")
async def get_roadmap_endpoint(subject: str, user: UserInfo = Depends(get_current_user)):
    try:
        steps = get_or_create_roadmap(user.id, subject)
        return steps
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update")
async def update_roadmap_endpoint(req: RoadmapUpdate, user: UserInfo = Depends(get_current_user)):
    try:
        steps = update_roadmap_topic_status(user.id, req.subject, req.topic, req.status)
        return steps
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
