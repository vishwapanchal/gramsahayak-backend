from fastapi import APIRouter, UploadFile, File, Form
from typing import List, Optional
from app.utils.s3 import upload_file_to_s3

router = APIRouter(prefix="/uploads", tags=["File Uploads"])

@router.post("/")
async def upload_files(
    reference_id: str = Form(...),
    files: Optional[List[UploadFile]] = File(None)
):
    uploaded_files = []

    if files:
        for file in files:
            file_url = upload_file_to_s3(
                file.file,
                file.filename,
                folder=f"uploads/{reference_id}"
            )
            uploaded_files.append({
                "file_name": file.filename,
                "file_url": file_url,
                "content_type": file.content_type
            })

    return {
        "message": "Upload successful",
        "reference_id": reference_id,
        "files": uploaded_files
    }
