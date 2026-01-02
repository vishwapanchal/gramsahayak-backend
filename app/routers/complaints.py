from fastapi import APIRouter, HTTPException, status, Form, UploadFile, File
from app.database import db
from app.schemas import ComplaintResponse
from typing import List, Optional
import boto3
import os
import uuid
from datetime import datetime
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/complaints", tags=["Complaints & Grievances"])

# --- AWS S3 CONFIGURATION ---
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")

s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
)

def upload_file_to_s3(file: UploadFile, folder: str = "complaints") -> str:
    """
    Uploads a file to S3 and returns the public URL.
    """
    try:
        # Generate unique filename
        file_extension = file.filename.split(".")[-1]
        unique_filename = f"{folder}/{uuid.uuid4()}.{file_extension}"
        
        # Upload
        s3_client.upload_fileobj(
            file.file,
            AWS_BUCKET_NAME,
            unique_filename,
            ExtraArgs={"ContentType": file.content_type}
        )
        
        # Construct URL
        url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{unique_filename}"
        return url
    except Exception as e:
        print(f"❌ S3 Upload Error: {str(e)}")
        return None

@router.post("/raise", status_code=status.HTTP_201_CREATED, response_model=ComplaintResponse)
async def raise_complaint(
    phone_number: str = Form(..., description="Registered Phone Number of the Villager"),
    complaint_name: str = Form(..., description="Title of the complaint"),
    complaint_desc: str = Form(..., description="Detailed description"),
    location: str = Form(..., description="Specific location (e.g., Ward 4)"),
    files: List[UploadFile] = File(default=None, description="Optional: Any number of files (Images, PDF, Video)")
):
    """
    Raises a new complaint with optional file attachments (S3).
    """
    
    # 1. Fetch Villager Details
    villager = await db.villagers.find_one({"phone_number": phone_number})
    if not villager:
        raise HTTPException(
            status_code=404, 
            detail="Villager not found with this phone number. Please register first."
        )
    
    village_name = villager["village_name"]

    # 2. Upload Files to S3 (Iterate over the list)
    uploaded_urls = []
    
    if files:
        for file in files:
            # Skip empty file objects if sent by mistake
            if file.filename:
                url = upload_file_to_s3(file)
                if url:
                    uploaded_urls.append(url)

    # 3. Create Complaint Object
    new_complaint = {
        "complaint_name": complaint_name,
        "complaint_desc": complaint_desc,
        "location": location,
        "villager_id": str(villager["_id"]),
        "villager_name": villager["name"],
        "villager_phone": phone_number,
        "village_name": village_name,
        "attachments": uploaded_urls,  # <--- Storing S3 URLs here
        "status": "Pending",
        "created_at": datetime.utcnow()
    }

    # Insert into 'complaints' collection
    result = await db.complaints.insert_one(new_complaint)
    complaint_id = result.inserted_id

    # 4. Link Complaint ID to Users (Official & Villager)
    
    # A. Link to Official
    official = await db.government_officials.find_one({"village_name": village_name})
    if official:
        await db.government_officials.update_one(
            {"_id": official["_id"]},
            {"$push": {"assigned_complaints": str(complaint_id)}}
        )

    # B. Link to Villager
    await db.villagers.update_one(
        {"_id": villager["_id"]},
        {"$push": {"complaints_raised": str(complaint_id)}}
    )

    # Return Response
    return {
        "id": str(complaint_id),
        "complaint_name": complaint_name,
        "complaint_desc": complaint_desc,
        "location": location,
        "status": "Pending",
        "village_name": village_name,
        "villager_phone": phone_number,
        "attachments": uploaded_urls,
        "created_at": new_complaint["created_at"]
    }
