from app.core.supabase_client import supabase
from datetime import datetime

class HistoryMessage:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content

def get_conversation_history(conversation_id: str, limit: int = 5) -> list[HistoryMessage]:
    res = supabase.table('messages').select('role, content, image_ocr_text, created_at') \
        .eq('conversation_id', conversation_id) \
        .order('created_at', desc=True) \
        .limit(limit) \
        .execute()
    
    data = res.data or []
    # Reverse to get chronological order
    data.reverse()
    
    formatted = []
    for m in data:
        content = m.get('content') or ""
        ocr = m.get('image_ocr_text')
        if ocr:
            content = f"{content}\n[Image content: {ocr}]".strip()
        formatted.append(HistoryMessage(role=m['role'], content=content))
    return formatted

def save_user_message(conversation_id: str, user_id: str, content: str = None, 
                      image_url: str = None, image_ocr_text: str = None):
    res = supabase.table('messages').insert({
        'conversation_id': conversation_id,
        'user_id': user_id,
        'role': 'user',
        'content': content,
        'image_url': image_url,
        'image_ocr_text': image_ocr_text
    }).execute()
    return res.data[0] if res.data else None

def save_assistant_message(conversation_id: str, user_id: str, content: str, topic_tags: list = None, is_correct: bool = None):
    topic_tags = topic_tags or []
    payload = {
        'conversation_id': conversation_id,
        'user_id': user_id,
        'role': 'assistant',
        'content': content,
        'topic_tags': topic_tags
    }
    if is_correct is not None:
        payload['is_correct'] = is_correct

    res = supabase.table('messages').insert(payload).execute()
    
    supabase.table('conversations').update({'updated_at': datetime.utcnow().isoformat()}).eq('id', conversation_id).execute()
    
    return res.data[0] if res.data else None
