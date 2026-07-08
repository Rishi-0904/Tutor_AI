from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
from starlette.concurrency import run_in_threadpool
from app.models.schemas import UserInfo, ChatResponse
from app.middleware.auth import get_current_user
from app.core.supabase_client import supabase
from app.services.history_service import get_conversation_history, save_user_message, save_assistant_message
from app.services.llm_service import generate_answer, generate_answer_stream, format_question_latex, process_image_with_gemini
from app.services.ocr_service import extract_text_from_image
from app.services.agent_service import run_agent_stream
from app.services.storage_service import upload_image_to_supabase
import json

router = APIRouter(tags=["chat"])

@router.get("/conversations")
async def get_conversations(user: UserInfo = Depends(get_current_user)):
    res = supabase.table('conversations').select('*').eq('user_id', user.id).order('updated_at', desc=True).execute()
    return res.data

@router.post("/conversations")
async def create_conversation(
    subject: str = Form("general"),
    title: Optional[str] = Form(None),
    user: UserInfo = Depends(get_current_user)
):
    res = supabase.table('conversations').insert({
        'user_id': user.id,
        'subject': subject,
        'title': title or f"New {subject} chat"
    }).execute()
    return res.data[0] if res.data else {}

@router.get("/conversations/{conversation_id}/messages")
async def get_messages(conversation_id: str, user: UserInfo = Depends(get_current_user)):
    # Verify owner
    conv = supabase.table('conversations').select('id').eq('id', conversation_id).eq('user_id', user.id).execute()
    if not conv.data:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    res = supabase.table('messages').select('*').eq('conversation_id', conversation_id).order('created_at', desc=False).execute()
    return res.data

@router.post("/chat", response_model=ChatResponse)
async def chat(
    conversationId: str = Form(...),
    content: Optional[str] = Form(""),
    image: Optional[UploadFile] = File(None),
    user: UserInfo = Depends(get_current_user)
):
    if not content.strip() and not image:
        raise HTTPException(status_code=400, detail="Content required")

    # Verify conversation
    conv = supabase.table('conversations').select('subject').eq('id', conversationId).eq('user_id', user.id).execute()
    if not conv.data:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    subject = conv.data[0].get("subject", "general")
    history = get_conversation_history(conversationId, limit=5)
    
    # Process Image if present
    full_content = content
    image_url = None
    extracted_text = None
    if image:
        image_bytes = await image.read()
        extracted_text = await run_in_threadpool(process_image_with_gemini, image_bytes=image_bytes)
        
        # Fallback to local OCR if Gemini fails
        if extracted_text.startswith("Error:"):
            print(f"[Chat] Gemini Vision failed, falling back to local OCR...")
            extracted_text = await run_in_threadpool(extract_text_from_image, image_bytes=image_bytes)
            
        full_content = f"{content}\n\n[Extracted from Image]:\n{extracted_text}" if content else extracted_text
        image_url = await run_in_threadpool(upload_image_to_supabase, image_bytes=image_bytes, file_name=image.filename)

    formatted_content = await run_in_threadpool(format_question_latex, question=full_content)
    
    user_msg = save_user_message(
        conversation_id=conversationId, 
        user_id=user.id, 
        content=formatted_content,
        image_url=image_url,
        image_ocr_text=extracted_text
    )
    
    # Execute agent
    ai_content = ""
    async for chunk in run_agent_stream(
        conversation_id=conversationId,
        user_id=user.id,
        message=formatted_content,
        subject=subject,
        history=history
    ):
        ai_content += chunk
        
    # Retrieve the saved message from database
    res = supabase.table('messages').select('*').eq('conversation_id', conversationId).eq('role', 'assistant').order('created_at', desc=True).limit(1).execute()
    ai_msg = res.data[0] if res.data else {"role": "assistant", "content": ai_content, "topic_tags": []}
    
    return ChatResponse(userMessage=user_msg, aiMessage=ai_msg)


@router.post("/chat/stream")
async def chat_stream(
    conversationId: str = Form(...),
    content: Optional[str] = Form(""),
    image: Optional[UploadFile] = File(None),
    user: UserInfo = Depends(get_current_user)
):
    if not content.strip() and not image:
        raise HTTPException(status_code=400, detail="Content required")

    # Verify conversation
    conv = supabase.table('conversations').select('subject').eq('id', conversationId).eq('user_id', user.id).execute()
    if not conv.data:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    subject = conv.data[0].get("subject", "general")
    history = get_conversation_history(conversationId, limit=5)
    
    # Process Image if present
    full_content = content
    image_url = None
    extracted_text = None
    if image:
        image_bytes = await image.read()
        extracted_text = await run_in_threadpool(process_image_with_gemini, image_bytes=image_bytes)
        
        # Fallback to local OCR if Gemini fails
        if extracted_text.startswith("Error:"):
            print(f"[Chat] Gemini Vision failed, falling back to local OCR...")
            extracted_text = await run_in_threadpool(extract_text_from_image, image_bytes=image_bytes)
            
        full_content = f"{content}\n\n[Extracted from Image]:\n{extracted_text}" if content else extracted_text
        image_url = await run_in_threadpool(upload_image_to_supabase, image_bytes=image_bytes, file_name=image.filename)

    # Skip format_question_latex for streaming — save the 1-2s Gemini round-trip.
    # The agent's generate_answer_stream() will still produce properly formatted LaTeX.
    message_content = full_content.strip()
    
    save_user_message(
        conversation_id=conversationId, 
        user_id=user.id, 
        content=message_content,
        image_url=image_url,
        image_ocr_text=extracted_text
    )
    
    async def event_generator():
        try:
            async for chunk in run_agent_stream(
                conversation_id=conversationId,
                user_id=user.id,
                message=message_content,
                subject=subject,
                history=history
            ):
                # Agent status events are prefixed with __STATUS__
                if isinstance(chunk, str) and chunk.startswith("__STATUS__"):
                    status_payload = chunk[len("__STATUS__"):]
                    yield f"data: {json.dumps({'type': 'agent_status', 'data': json.loads(status_payload)})}\n\n"
                else:
                    yield f"data: {json.dumps({'content': chunk})}\n\n"
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            print("Stream error:", str(e))
            yield f"data: {json.dumps({'content': f'\\n\\nError: {str(e)}'})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disable nginx/proxy buffering
            "Connection": "keep-alive",
        }
    )


from pydantic import BaseModel

class SaveSketchRequest(BaseModel):
    conversationId: str
    title: str
    svgData: str

@router.post("/conversations/sketch")
async def save_sketch_endpoint(
    req: SaveSketchRequest,
    user: UserInfo = Depends(get_current_user)
):
    from app.services.mcp_service import mcp_service
    res = await mcp_service.save_sketch(
        user_id=user.id,
        conversation_id=req.conversationId,
        title=req.title,
        svg_data=req.svgData
    )
    if not res.get("success"):
        raise HTTPException(status_code=500, detail=res.get("error", "Failed to save sketch"))
    return res

@router.get("/conversations/{conversation_id}/sketches")
async def get_sketches_endpoint(
    conversation_id: str,
    user: UserInfo = Depends(get_current_user)
):
    from app.services.mcp_service import mcp_service
    sketches = await mcp_service.load_sketches(
        user_id=user.id,
        conversation_id=conversation_id
    )
    return sketches

