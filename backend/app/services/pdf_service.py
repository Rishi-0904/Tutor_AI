import io
import pypdf
from typing import List
from app.core.supabase_client import supabase
from app.core.config import settings
from google import genai as google_genai

def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extracts all text pages from a raw PDF byte stream."""
    pdf_file = io.BytesIO(pdf_bytes)
    reader = pypdf.PdfReader(pdf_file)
    text_list = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            text_list.append(text)
    return "\n\n".join(text_list)

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
    """Chunks text into small paragraphs of chunk_size with overlap."""
    chunks = []
    text_len = len(text)
    i = 0
    while i < text_len:
        # Fetch chunk of character length chunk_size
        chunk = text[i : i + chunk_size]
        chunks.append(chunk)
        i += (chunk_size - overlap)
        
    return [c.strip() for c in chunks if c.strip()]

async def process_pdf_background(pdf_id: str, pdf_bytes: bytes, user_id: str):
    """
    Background worker that runs chunking, embeddings, and vector saving.
    Executed in a background thread to prevent API connection freezes.
    """
    print(f"[PDF Background] Starting text extraction for doc {pdf_id}...")
    try:
        # 1. Parse text
        text = extract_text_from_pdf_bytes(pdf_bytes)
        if not text.strip():
            raise ValueError("No text extracted from PDF notes.")
            
        # 2. Chunk text
        chunks = chunk_text(text, chunk_size=500, overlap=100)
        print(f"[PDF Background] Extracted {len(chunks)} chunks from document.")
        
        # 3. Generate Embeddings & Save to Supabase Vector
        api_key = settings.gemini_api_key
        if not api_key:
            raise ValueError("Gemini API key is not configured.")
            
        client = google_genai.Client(api_key=api_key)
        
        # Process chunks and save them
        for idx, chunk in enumerate(chunks):
            # Fetch embedding from Gemini API (768 dimensions)
            response = client.models.embed_content(
                model="gemini-embedding-2",
                contents=chunk,
                config={"output_dimensionality": 768}
            )
            embedding_vector = response.embeddings[0].values
            
            # Save chunk to supabase pdf_chunks
            supabase.table('pdf_chunks').insert({
                'pdf_id': pdf_id,
                'chunk_index': idx,
                'content': chunk,
                'embedding': embedding_vector
            }).execute()
            
        # 4. Update status to completed
        supabase.table('pdf_documents').update({'status': 'completed'}).eq('id', pdf_id).execute()
        print(f"[PDF Background] Successfully processed and indexed doc {pdf_id}!")
        
    except Exception as e:
        print(f"[PDF Background] Error processing document {pdf_id}: {e}")
        try:
            supabase.table('pdf_documents').update({'status': 'failed'}).eq('id', pdf_id).execute()
        except Exception as db_err:
            print(f"[PDF Background] Failed to save error status to database: {db_err}")
