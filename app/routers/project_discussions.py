from fastapi import APIRouter, HTTPException, status, Query, Body
from app.database import db
from app.schemas import ProjectChatCreate, ProjectChatResponse
from typing import List
from datetime import datetime
from bson import ObjectId

router = APIRouter(prefix="/project-chat", tags=["Project Discussions (Private)"])

# --- HELPER: Validate Access ---
async def validate_access(project_id: str, user_id: str, role: str):
    """
    Ensures the user belongs to the project and village context.
    Returns: (Project Dict, User Name)
    """
    # 1. Verify Project Exists
    try:
        p_oid = ObjectId(project_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid Project ID")
    
    project = await db.projects.find_one({"_id": p_oid})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    user_name = ""

    # 2. CONTRACTOR VALIDATION
    # Must be the specific contractor assigned to this project
    if role == "contractor":
        # Check if user exists as contractor
        # Note: input user_id here is expected to be the 'contractor_id' (e.g., CNT-2025-003) 
        # based on your schema usage in other files, OR the MongoDB _id.
        # Let's support the `contractor_id` string field as that's what is in the project.
        
        if project.get("contractor_id") != user_id:
             raise HTTPException(status_code=403, detail="Access Denied: You are not the assigned contractor for this project.")
        
        # Get Name for UI
        contractor = await db.contractors.find_one({"contractor_id": user_id})
        if contractor:
            user_name = contractor.get("name", "Unknown Contractor")
        else:
             raise HTTPException(status_code=404, detail="Contractor profile not found")

    # 3. OFFICIAL VALIDATION
    # Must belong to the SAME VILLAGE as the project
    elif role == "official":
        # Here user_id is likely the MongoDB _id or government_id. 
        # Let's assume government_id for consistency with your other auth logic, 
        # or handle ObjectId if you pass that. 
        # We will try to find by government_id first.
        
        official = await db.government_officials.find_one({"government_id": user_id})
        if not official:
            # Try ObjectId just in case
            try:
                official = await db.government_officials.find_one({"_id": ObjectId(user_id)})
            except:
                pass
        
        if not official:
            raise HTTPException(status_code=404, detail="Official not found")

        # STRICT CHECK: Official's Village == Project's Village
        if official["village_name"] != project["village_name"]:
            raise HTTPException(
                status_code=403, 
                detail=f"Access Denied: This project is in {project['village_name']}, but you are assigned to {official['village_name']}."
            )
        
        user_name = official.get("name", "Official")

    else:
        raise HTTPException(status_code=400, detail="Invalid Role. Must be 'contractor' or 'official'.")

    return project, user_name

# --- 1. SEND MESSAGE ---
@router.post("/send", response_model=ProjectChatResponse, status_code=status.HTTP_201_CREATED)
async def send_message(message: ProjectChatCreate):
    
    # Run Validation
    project, sender_name = await validate_access(message.project_id, message.sender_id, message.sender_role)

    # Create Message Record
    new_msg = {
        "project_id": message.project_id,
        "sender_id": message.sender_id,
        "sender_role": message.sender_role,
        "sender_name": sender_name,
        "content": message.content,
        "created_at": datetime.utcnow()
    }

    result = await db.project_discussions.insert_one(new_msg)
    
    new_msg["id"] = str(result.inserted_id)
    return new_msg

# --- 2. GET MESSAGES (History) ---
@router.get("/{project_id}", response_model=List[ProjectChatResponse])
async def get_messages(
    project_id: str,
    user_id: str = Query(..., description="Your ID (Contractor ID or Government ID)"),
    role: str = Query(..., description="'contractor' or 'official'")
):
    # Run Validation (Security Check)
    # Even to view messages, you must be authorized
    await validate_access(project_id, user_id, role)

    # Fetch
    cursor = db.project_discussions.find({"project_id": project_id}).sort("created_at", 1)
    messages = await cursor.to_list(length=1000)

    results = []
    for m in messages:
        m["id"] = str(m["_id"])
        results.append(m)
    
    return results
