from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from app.middleware.auth import get_current_user
from app.models.schemas import UserInfo
from app.services.ocr_service import extract_parsed_from_image
from app.services.pdf_service import process_pdf_background
from app.core.supabase_client import supabase
from starlette.concurrency import run_in_threadpool

router = APIRouter(prefix="/ocr", tags=["ocr"])

@router.post("/extract")
async def extract_text(image: UploadFile = File(...), user: UserInfo = Depends(get_current_user)):
    if not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        content = await image.read()
        # Run OCR in threadpool to avoid blocking the event loop
        result = await run_in_threadpool(extract_parsed_from_image, content)
        # result = { subject, question, raw }
        return {
            "text":     result["raw"],       # full raw model output (backwards-compat)
            "subject":  result["subject"],   # detected subject
            "question": result["question"],  # extracted question text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/pdf/upload")
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: UserInfo = Depends(get_current_user)
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF document")
        
    try:
        # 1. Insert document reference in Supabase
        res = supabase.table('pdf_documents').insert({
            'user_id': user.id,
            'filename': file.filename,
            'status': 'processing'
        }).execute()
        
        if not res.data:
            raise HTTPException(status_code=500, detail="Failed to initialize PDF notes reference")
            
        doc_data = res.data[0]
        pdf_id = doc_data["id"]
        
        # 2. Extract raw file bytes
        file_bytes = await file.read()
        
        # 3. Spawn background chunking and embedding task
        background_tasks.add_task(
            process_pdf_background,
            pdf_id=pdf_id,
            pdf_bytes=file_bytes,
            user_id=user.id
        )
        
        return {
            "success": True,
            "document_id": pdf_id,
            "filename": file.filename,
            "status": "processing",
            "message": "PDF notes upload complete. Processing and indexing in background..."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
