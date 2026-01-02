from fastapi import APIRouter, HTTPException, status, Query
from app.database import db
from app.schemas import ProjectCreate, ProjectResponse
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

router = APIRouter(prefix="/projects", tags=["Projects & Development"])

# --- HELPER: Verify Official Role ---
async def verify_official(user_id: str):
    """
    Checks if the provided ID belongs to a Government Official.
    Throws 403 error if not.
    """
    try:
        obj_id = ObjectId(user_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid User ID format")

    # Check strictly in the 'government_officials' collection
    official = await db.government_officials.find_one({"_id": obj_id})
    
    if not official:
        raise HTTPException(
            status_code=403, 
            detail="Access Denied. Only Government Officials can perform this action."
        )
    return official

# --- 1. CREATE A NEW PROJECT (Restricted) ---
@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_project(
    project: ProjectCreate,
    official_id: str = Query(..., description="Your Government Official ID (from Login)")
):
    # 1. Security Check
    await verify_official(official_id)

    # 2. Proceed to Create
    new_project = project.model_dump()
    new_project["created_at"] = datetime.utcnow()
    new_project["milestones"] = ["Project Initiated"]
    
    result = await db.projects.insert_one(new_project)
    
    return {"message": "Project created successfully", "id": str(result.inserted_id)}

# --- 2. GET PROJECTS (Public - Filter by Village) ---
@router.get("/", response_model=List[ProjectResponse])
async def get_all_projects(
    village_name: str = Query(..., description="The name of the village to fetch projects for")
):
    query = {"village_name": village_name}
    projects = await db.projects.find(query).sort("created_at", -1).to_list(100)
    
    results = []
    for p in projects:
        p["id"] = str(p["_id"])
        results.append(p)
    return results

# --- 3. GET SINGLE PROJECT (Public) ---
@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    try:
        obj_id = ObjectId(project_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid Project ID")
        
    project = await db.projects.find_one({"_id": obj_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    project["id"] = str(project["_id"])
    return project

# --- 4. UPDATE STATUS (Restricted) ---
@router.patch("/{project_id}/status")
async def update_status(
    project_id: str, 
    status: str, 
    official_id: str = Query(..., description="Your Government Official ID"),
    new_milestone: str = None
):
    # 1. Security Check
    await verify_official(official_id)

    # 2. Proceed to Update
    try:
        obj_id = ObjectId(project_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid Project ID")

    update_data = {"$set": {"status": status}}
    
    if new_milestone:
        update_data["$push"] = {"milestones": new_milestone}

    result = await db.projects.update_one({"_id": obj_id}, update_data)
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Project not found or no change")
        
    return {"message": "Project status updated"}
