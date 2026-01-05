from fastapi import APIRouter, HTTPException, status, Query
from app.database import db
from pydantic import BaseModel
from datetime import datetime
from bson import ObjectId
from typing import List

router = APIRouter(prefix="/secure-chat", tags=["Official-Contractor Confidential"])

# --- Models ---
class MessageCreate(BaseModel):
    sender_id: str
    receiver_id: str
    content: str

class MessageResponse(BaseModel):
    id: str
    sender_id: str
    sender_role: str
    receiver_id: str
    receiver_role: str
    content: str
    village_name: str
    timestamp: datetime

# --- Helper: Identify User & Context ---
async def get_identity(user_id: str):
    """
    Resolves a User ID to either an Official or a Contractor.
    Returns: (role, context_data)
    """
    try:
        oid = ObjectId(user_id)
    except:
        return None, None
    
    # 1. Check if Government Official
    off = await db.government_officials.find_one({"_id": oid})
    if off:
        return "official", {"village": off["village_name"]}
        
    # 2. Check if Contractor
    con = await db.contractors.find_one({"_id": oid})
    if con:
        return "contractor", {"c_id": con["contractor_id"]}
        
    return None, None

# --- API Endpoints ---

@router.post("/send", response_model=MessageResponse)
async def send_message(msg: MessageCreate):
    """
    Sends a message between an Official and a Contractor.
    ENFORCES: They must belong to the same village (verified via assigned projects).
    """
    # 1. Identify Participants
    role1, data1 = await get_identity(msg.sender_id)
    role2, data2 = await get_identity(msg.receiver_id)

    if not role1 or not role2:
        raise HTTPException(status_code=404, detail="One or both users not found.")

    # 2. Enforce Role Constraints (One Official, One Contractor)
    roles = [role1, role2]
    if "official" not in roles or "contractor" not in roles:
        raise HTTPException(
            status_code=403, 
            detail="Restricted Channel: Chat allowed ONLY between a Government Official and a Contractor."
        )

    # 3. Determine Context (Village vs Contractor ID)
    if role1 == "official":
        target_village = data1["village"]
        contractor_biz_id = data2["c_id"]
    else:
        target_village = data2["village"]
        contractor_biz_id = data1["c_id"]

    # 4. Enforce "Same Village" Rule
    # Logic: A contractor 'belongs' to a village if they have an active project there.
    project_link = await db.projects.find_one({
        "contractor_id": contractor_biz_id,
        "village_name": target_village
    })

    if not project_link:
        raise HTTPException(
            status_code=403, 
            detail=f"Access Denied: Contractor {contractor_biz_id} has no assigned projects in {target_village}."
        )

    # 5. Save Message
    doc = {
        "sender_id": msg.sender_id,
        "sender_role": role1,
        "receiver_id": msg.receiver_id,
        "receiver_role": role2,
        "content": msg.content,
        "village_name": target_village,
        "timestamp": datetime.utcnow()
    }
    
    result = await db.secure_chats.insert_one(doc)
    
    return {**doc, "id": str(result.inserted_id)}

@router.get("/history", response_model=List[MessageResponse])
async def get_chat_history(
    user1: str = Query(..., description="User ID 1"), 
    user2: str = Query(..., description="User ID 2")
):
    """
    Fetch chat history between two specific users.
    """
    cursor = db.secure_chats.find({
        "$or": [
            {"sender_id": user1, "receiver_id": user2},
            {"sender_id": user2, "receiver_id": user1}
        ]
    }).sort("timestamp", 1)
    
    messages = await cursor.to_list(1000)
    
    results = []
    for m in messages:
        m["id"] = str(m["_id"])
        results.append(m)
    return results
