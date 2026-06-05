import uuid
from typing import Optional
from app.core.supabase_client import supabase
from app.core.config import settings

def upload_image_to_supabase(image_bytes: bytes, file_name: Optional[str] = None) -> Optional[str]:
    """
    Uploads raw image bytes to the 'question-images' bucket in Supabase.
    Generates a unique name if not provided.
    """
    # 1. Check if Supabase client is configured
    if not settings.supabase_url or not settings.supabase_service_key or settings.supabase_url == "http://localhost":
        print("[Storage] Supabase is not configured. Skipping image upload.")
        return None
        
    try:
        # Generate unique filename to avoid naming conflicts
        ext = "jpg"
        if file_name and "." in file_name:
            ext = file_name.split(".")[-1]
            
        unique_name = f"{uuid.uuid4()}.{ext}"
        print(f"[Storage] Uploading image as {unique_name} to bucket 'question-images'...")
        
        # Upload using the service role client (bypasses RLS)
        res = supabase.storage.from_("question-images").upload(
            path=unique_name,
            file=image_bytes,
            file_options={"content-type": f"image/{ext}"}
        )
        
        # Retrieve and return the public URL
        url = supabase.storage.from_("question-images").get_public_url(unique_name)
        print(f"[Storage] Image uploaded successfully. Public URL: {url}")
        return url
    except Exception as e:
        print(f"[Storage] Error uploading image: {e}")
        return None
