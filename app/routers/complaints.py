from fastapi import APIRouter, HTTPException, status, Form, UploadFile, File, Path
from app.database import db
from app.schemas import ComplaintResponse
from app.utils.s3 import upload_file_to_s3
from typing import List, Optional
from datetime import datetime

router = APIRouter(prefix="/complaints", tags=["Complaints & Grievances"])

# 1. RAISE COMPLAINT (Integrated Uploads)
@router.post("/raise", status_code=status.HTTP_201_CREATED, response_model=ComplaintResponse)
async def raise_complaint(
    phone_number: str = Form(..., description="Registered Phone Number"),
    complaint_name: str = Form(..., description="Title"),
    complaint_desc: str = Form(..., description="Description"),
    location: str = Form(..., description="Location"),
    files: List[UploadFile] = File(default=None, description="Optional files to upload")
):
    # A. Fetch Villager
    villager = await db.villagers.find_one({"phone_number": phone_number})
    if not villager:
        raise HTTPException(status_code=404, detail="Villager not found.")
    
    village_name = villager["village_name"]

    # B. Handle File Uploads (INTEGRATED HERE)
    uploaded_urls = []
    if files:
        for file in files:
            if file.filename:
                print(f"📤 Uploading: {file.filename}")
                # Call utility function
                url = upload_file_to_s3(file.file, file.filename, folder="complaints")
                if url:
                    uploaded_urls.append(url)
                    print(f"✅ Uploaded: {url}")

    # C. Create Complaint Record
    new_complaint = {
        "complaint_name": complaint_name,
        "complaint_desc": complaint_desc,
        "location": location,
        "villager_id": str(villager["_id"]),
        "villager_name": villager["name"],
        "villager_phone": phone_number,
        "village_name": village_name,
        "attachments": uploaded_urls,  # URLs stored here
        "status": "Pending",
        "created_at": datetime.utcnow()
    }

    result = await db.complaints.insert_one(new_complaint)
    complaint_id = result.inserted_id

    # D. Link to Official & Villager
    await db.government_officials.update_one(
        {"village_name": village_name},
        {"$push": {"assigned_complaints": str(complaint_id)}}
    )
    await db.villagers.update_one(
        {"_id": villager["_id"]},
        {"$push": {"complaints_raised": str(complaint_id)}}
    )

    # E. Return Response
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

# 2. FETCH COMPLAINTS
@router.get("/villager/{phone_number}", response_model=List[ComplaintResponse])
async def get_complaints_by_villager(phone_number: str):
    complaints = await db.complaints.find({"villager_phone": phone_number}).sort("created_at", -1).to_list(100)
    results = []
    for c in complaints:
        c["id"] = str(c["_id"])
        if "attachments" not in c: c["attachments"] = []
        results.append(c)
    return results
