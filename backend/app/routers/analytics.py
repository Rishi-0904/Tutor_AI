from fastapi import APIRouter, Depends
from app.models.schemas import UserInfo
from app.middleware.auth import get_current_user
from app.core.supabase_client import supabase
from datetime import datetime, timedelta, timezone

router = APIRouter(tags=["analytics"])


@router.get("/analytics/summary")
async def get_summary(user: UserInfo = Depends(get_current_user)):
    """High-level performance summary for the current user."""
    mastery_res = supabase.table("topic_mastery").select("score").eq("user_id", user.id).execute()
    scores = [r["score"] for r in (mastery_res.data or [])]

    sessions_res = supabase.table("learning_sessions").select("id,started_at").eq("user_id", user.id).order("started_at", desc=False).execute()
    sessions = sessions_res.data or []

    total_mastered = sum(1 for s in scores if s >= 80)
    avg_mastery = round(sum(scores) / len(scores), 1) if scores else 0

    # Streak: count consecutive days with at least 1 session (working backwards from today)
    streak = 0
    if sessions:
        today = datetime.now(timezone.utc).date()
        day_set = set()
        for s in sessions:
            try:
                d = datetime.fromisoformat(s["started_at"].replace("Z", "+00:00")).date()
                day_set.add(d)
            except Exception:
                pass
        check = today
        while check in day_set:
            streak += 1
            check -= timedelta(days=1)

    return {
        "total_topics": len(scores),
        "topics_mastered": total_mastered,
        "avg_mastery": avg_mastery,
        "total_sessions": len(sessions),
        "streak_days": streak,
    }


@router.get("/analytics/mastery")
async def get_mastery(user: UserInfo = Depends(get_current_user)):
    """Returns per-topic mastery scores grouped by subject."""
    res = supabase.table("topic_mastery").select("topic,score,updated_at").eq("user_id", user.id).order("score", desc=False).execute()
    topics = res.data or []

    grouped: dict = {}
    for t in topics:
        subj = t.get("subject", "general")
        grouped.setdefault(subj, []).append({
            "topic": t["topic"],
            "score": t["score"],
            "updated_at": t.get("updated_at"),
        })
    return grouped


@router.get("/analytics/sessions")
async def get_sessions(user: UserInfo = Depends(get_current_user)):
    """Returns last 30 learning sessions with duration and mastery delta."""
    res = supabase.table("learning_sessions").select(
        "id,topic,subject,started_at,ended_at,score_before,score_after"
    ).eq("user_id", user.id).order("started_at", desc=True).limit(30).execute()

    sessions = res.data or []
    for s in sessions:
        # Compute duration in minutes
        try:
            start = datetime.fromisoformat(s["started_at"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(s["ended_at"].replace("Z", "+00:00")) if s.get("ended_at") else datetime.now(timezone.utc)
            s["duration_min"] = round((end - start).total_seconds() / 60, 1)
        except Exception:
            s["duration_min"] = None
        s["delta"] = (
            round(s["score_after"] - s["score_before"], 1)
            if s.get("score_after") is not None and s.get("score_before") is not None
            else None
        )
    return sessions


@router.get("/analytics/velocity")
async def get_velocity(user: UserInfo = Depends(get_current_user)):
    """Returns daily avg mastery delta for the last 7 days (learning velocity)."""
    since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    res = supabase.table("learning_sessions").select(
        "started_at,score_before,score_after"
    ).eq("user_id", user.id).gte("started_at", since).order("started_at", desc=False).execute()

    sessions = res.data or []

    # Bucket by day
    daily: dict = {}
    for s in sessions:
        if s.get("score_before") is None or s.get("score_after") is None:
            continue
        try:
            day = datetime.fromisoformat(s["started_at"].replace("Z", "+00:00")).strftime("%Y-%m-%d")
        except Exception:
            continue
        daily.setdefault(day, []).append(s["score_after"] - s["score_before"])

    result = []
    for i in range(7):
        day = (datetime.now(timezone.utc) - timedelta(days=6 - i)).strftime("%Y-%m-%d")
        deltas = daily.get(day, [])
        result.append({
            "day": day,
            "avg_delta": round(sum(deltas) / len(deltas), 2) if deltas else 0,
            "sessions": len(deltas),
        })
    return result
