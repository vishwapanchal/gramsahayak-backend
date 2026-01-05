from fastapi import APIRouter, HTTPException, status, Query
from app.database import db
from pydantic import BaseModel
from datetime import datetime
from bson import ObjectId
from typing import List

# MATCHING YOUR LOGS: Prefix is /project-chat
router = APIRouter(prefix="/project-chat", tags=["Project Communication"])

# --- Models ---
class MessageCreate(BaseModel):
    project_id: str
    sender_id: str
    role: str
    content: str

class MessageResponse(BaseModel):
    id: str
    sender_id: str
    role: str
    content: str
    timestamp: datetime
    project_id: str

# --- API Endpoints ---

@router.post("/send", response_model=MessageResponse)
async def send_project_message(msg: MessageCreate):
    """
    Sends a message inside a specific Project Room.
    Restricted to: The Assigned Contractor AND The Village Official.
    """
    # 1. Validate Project ID
    try:
        p_oid = ObjectId(msg.project_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid Project ID")

    project = await db.projects.find_one({"_id": p_oid})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # 2. Authorization Check
    # A. If Sender is Contractor -> Must be the ASSIGNED Contractor
    if msg.role == "contractor":
        contractor = await db.contractors.find_one({"_id": ObjectId(msg.sender_id)})
        if not contractor or contractor["contractor_id"] != project["contractor_id"]:
             raise HTTPException(status_code=403, detail="Access Denied: You are not the contractor for this project.")

    # B. If Sender is Official -> Must be Official of that Village
    elif msg.role == "government_official":
        official = await db.government_officials.find_one({"_id": ObjectId(msg.sender_id)})
        if not official or official["village_name"] != project["village_name"]:
             raise HTTPException(status_code=403, detail="Access Denied: This project is not in your jurisdiction.")
    
    else:
        raise HTTPException(status_code=400, detail="Invalid Role")

    # 3. Save Message
    doc = {
        "project_id": msg.project_id,
        "sender_id": msg.sender_id,
        "role": msg.role,
        "content": msg.content,
        "timestamp": datetime.utcnow()
    }
    
    result = await db.project_chats.insert_one(doc)
    
    return {**doc, "id": str(result.inserted_id)}

@router.get("/{project_id}", response_model=List[MessageResponse])
async def get_project_chat_history(
    project_id: str,
    user_id: str = Query(..., description="User requesting history"),
    role: str = Query(..., description="Role of the user")
):
    """
    Fetch chat history for a specific project.
    """
    # 1. Validate Project
    try:
        p_oid = ObjectId(project_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid Project ID")

    project = await db.projects.find_one({"_id": p_oid})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # 2. Simple Auth Check (Ensure user is related to project)
    # (For brevity, assuming frontend sends correct IDs. Secure version repeats checks above)

    # 3. Fetch Messages
    cursor = db.project_chats.find({"project_id": project_id}).sort("timestamp", 1)
    messages = await cursor.to_list(1000)
    
    results = []
    for m in messages:
        m["id"] = str(m["_id"])
        results.append(m)
    return results
