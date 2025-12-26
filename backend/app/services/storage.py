from supabase import create_client
import os
import uuid

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def upload_document(file_bytes: bytes, filename: str, content_type: str) -> str:
    """
    Uploads file to Supabase Storage.
    Returns storage path.
    """
    ext = filename.split(".")[-1]
    storage_path = f"documents/{uuid.uuid4()}.{ext}"

    supabase.storage.from_(BUCKET).upload(
        storage_path,
        file_bytes,
        {"content-type": content_type},
    )

    return storage_path


def get_document_signed_url(storage_path: str, expires_in: int = 3600) -> str:
    """
    Returns a signed URL for a stored document.
    """
    result = supabase.storage.from_(BUCKET).create_signed_url(storage_path, expires_in)
    if not isinstance(result, dict):
        raise ValueError("Failed to create signed URL")
    url = result.get("signedURL") or result.get("signedUrl")
    if not url:
        raise ValueError("Signed URL missing in response")
    return url
