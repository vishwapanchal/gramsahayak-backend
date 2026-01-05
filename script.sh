#!/bin/bash

echo "🚀 Updating Schema and User Router for Contractor Dashboard..."

# ==========================================
# 1. Update app/schemas.py
#    - Adds ProjectSummary, ContractorStats
#    - Adds ContractorDashboardResponse
# ==========================================
echo "📝 Updating 'app/schemas.py'..."

cat <<'EOF' > app/schemas.py
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime

# --- Villager Schemas ---
class VillagerSignup(BaseModel):
    name: str
    gender: str
    age: int
    email: EmailStr
    phone_number: str
    village_name: str
    taluk: str
    district: str
    state: str
    password: str
    role: str = "villager"

    @validator('phone_number')
    def validate_phone(cls, v):
        if not v.isdigit() or len(v) != 10:
            raise ValueError('Phone number must be exactly 10 digits')
        return v

class VillagerLogin(BaseModel):
    phone_number: str
    password: str

# --- Contractor Schemas ---
class ContractorLogin(BaseModel):
    contractor_id: str
    password: str

class ContractorCreate(BaseModel):
    name: str
    email: EmailStr
    phone_number: str
    contractor_id: str
    password: str
    role: str = "contractor"

# --- Government Official Schemas ---
class OfficialLogin(BaseModel):
    government_id: str
    password: str

class OfficialCreate(BaseModel):
    name: str
    email: EmailStr
    government_id: str
    village_name: str
    password: str
    role: str = "government_official"

# --- User Response Schemas ---
class VillagerResponse(BaseModel):
    id: str
    name: str
    gender: str
    age: int
    email: EmailStr
    phone_number: str
    village_name: str
    taluk: str
    district: str
    state: str
    role: str
    govt_official_id: Optional[str] = None
    complaints_raised: List[str] = []
    anonymous_identity: Optional[str] = None

class ContractorResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    phone_number: str
    contractor_id: str
    role: str

class OfficialResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    government_id: str
    village_name: str
    role: str
    assigned_complaints: List[str] = []

# --- Community Discussion Models ---
class DiscussionComment(BaseModel):
    user_name: str
    user_role: str
    content: str
    created_at: datetime

class DiscussionCreate(BaseModel):
    content: str
    category: str = "General"

class CommentCreate(BaseModel):
    content: str

class DiscussionResponse(BaseModel):
    id: str
    village_name: str
    user_name: str
    user_role: str
    content: str
    category: str
    created_at: datetime
    upvotes: int
    replies: List[DiscussionComment] = []
    image_url: Optional[str] = None

# --- AI Insight Models ---
class InsightCreate(BaseModel):
    period_start: datetime
    period_end: datetime
    summary: str
    top_issues: list[str]
    sentiment_score: float
    suggested_actions: list[str]

class InsightResponse(InsightCreate):
    id: str
    generated_at: datetime

# --- Project Schemas ---
class ProjectCreate(BaseModel):
    project_name: str
    description: str
    category: str
    village_name: str
    location: str
    contractor_name: str
    contractor_id: str
    contractor_address: str
    allocated_budget: float
    approved_by: str
    start_date: datetime
    due_date: datetime
    status: str = "Pending"
    images: list[str] = []

class ProjectResponse(ProjectCreate):
    id: str
    created_at: datetime
    milestones: list[str] = []

# --- Dashboard Schemas ---
class DashboardStats(BaseModel):
    budget_used: float
    issues_resolved: int
    village_mood: str
    personal_impact: int
    next_meeting: str

# --- Government Schemes Schemas ---
class SchemeBase(BaseModel):
    scheme_id: str
    scheme_name: str
    scheme_desc: str
    scheme_dept: str

class SchemeResponse(SchemeBase):
    id: str

# --- Proposed Projects Schemas ---
class ProposedProjectCreate(BaseModel):
    village_id: str
    proposed_project_title: str

class ProposedProjectResponse(BaseModel):
    id: str
    village_id: str
    proposed_project_title: str
    status: str
    created_at: datetime

# --- Complaint Schemas ---
class ComplaintResponse(BaseModel):
    id: str
    complaint_name: str
    complaint_desc: str
    location: str
    status: str
    village_name: str
    villager_phone: str
    attachments: List[str]
    created_at: datetime

# ==========================================
# NEW: CONTRACTOR DASHBOARD SCHEMAS
# ==========================================

class ProjectSummary(BaseModel):
    id: str
    project_name: str
    status: str
    allocated_budget: float
    location: str
    start_date: datetime

class ContractorStats(BaseModel):
    total_contract_value: float
    active_projects_count: int
    projects_completed_count: int
    pending_issues_count: int

class ContractorDashboardResponse(BaseModel):
    id: str
    name: str
    email: str  # using str to avoid strict email validation errors
    phone_number: str
    contractor_id: str
    role: str
    
    # New Dashboard Data
    stats: ContractorStats
    active_projects: List[ProjectSummary]
EOF

# ==========================================
# 2. Update app/routers/users.py
#    - Modifies get_contractor_by_id to fetch stats & projects
# ==========================================
echo "📝 Updating 'app/routers/users.py'..."

cat <<'EOF' > app/routers/users.py
from fastapi import APIRouter, HTTPException, status
from app.database import db
from app.schemas import (
    VillagerResponse, 
    ContractorResponse, 
    OfficialResponse, 
    ContractorDashboardResponse
)
from typing import List

router = APIRouter(prefix="/users", tags=["User Management"])

# ==========================
# 1. FETCH ALL USERS
# ==========================

@router.get("/villagers", response_model=List[VillagerResponse])
async def get_all_villagers():
    """Fetch all registered villagers with full details"""
    users = await db.villagers.find().to_list(1000)
    for user in users:
        user["id"] = str(user["_id"])
        # Ensure optional list fields exist if DB record is old
        if "complaints_raised" not in user:
            user["complaints_raised"] = []
    return users

@router.get("/contractors", response_model=List[ContractorResponse])
async def get_all_contractors():
    """Fetch all registered contractors"""
    users = await db.contractors.find().to_list(1000)
    for user in users:
        user["id"] = str(user["_id"])
    return users

@router.get("/officials", response_model=List[OfficialResponse])
async def get_all_officials():
    """Fetch all officials with assigned complaints"""
    users = await db.government_officials.find().to_list(1000)
    for user in users:
        user["id"] = str(user["_id"])
        # Ensure optional list fields exist
        if "assigned_complaints" not in user:
            user["assigned_complaints"] = []
    return users

# ==========================
# 2. FETCH SINGLE USER
# ==========================

@router.get("/villagers/{phone_number}", response_model=VillagerResponse)
async def get_villager_by_phone(phone_number: str):
    """Fetch a single villager by Phone Number"""
    user = await db.villagers.find_one({"phone_number": phone_number})
    if not user:
        raise HTTPException(status_code=404, detail="Villager not found")
    
    user["id"] = str(user["_id"])
    if "complaints_raised" not in user:
        user["complaints_raised"] = []
    return user

@router.get("/contractors/{contractor_id}", response_model=ContractorDashboardResponse)
async def get_contractor_by_id(contractor_id: str):
    """
    Fetch contractor profile + dashboard stats + active projects
    """
    # 1. Fetch Contractor Profile
    user = await db.contractors.find_one({"contractor_id": contractor_id})
    if not user:
        raise HTTPException(status_code=404, detail="Contractor not found")
    
    user["id"] = str(user["_id"])

    # 2. Fetch Projects assigned to this Contractor
    cursor = db.projects.find({"contractor_id": contractor_id})
    projects_list = await cursor.to_list(length=1000)

    # 3. Calculate Dashboard Statistics
    total_value = 0.0
    active_count = 0
    completed_count = 0
    active_projects_data = []

    for p in projects_list:
        p_status = p.get("status", "Pending")
        budget = float(p.get("allocated_budget", 0))

        # Sum up total contract value
        total_value += budget

        # Count Active vs Completed
        if p_status == "Completed":
            completed_count += 1
        else:
            active_count += 1
            # Add to the list of active projects
            active_projects_data.append({
                "id": str(p["_id"]),
                "project_name": p.get("project_name", "Untitled Project"),
                "status": p_status,
                "allocated_budget": budget,
                "location": p.get("location", "Unknown"),
                "start_date": p.get("start_date")
            })

    # 4. Construct the Final Response
    response_data = {
        **user,
        "stats": {
            "total_contract_value": total_value,
            "active_projects_count": active_count,
            "projects_completed_count": completed_count,
            "pending_issues_count": 0  # Placeholder
        },
        "active_projects": active_projects_data
    }

    return response_data

@router.get("/officials/{government_id}", response_model=OfficialResponse)
async def get_official_by_id(government_id: str):
    """Fetch a single official by Government ID"""
    user = await db.government_officials.find_one({"government_id": government_id})
    if not user:
        raise HTTPException(status_code=404, detail="Official not found")
    
    user["id"] = str(user["_id"])
    if "assigned_complaints" not in user:
        user["assigned_complaints"] = []
    return user
EOF

echo "---------------------------------------------------"
echo "✅ SUCCESS: Schemas and Contractor Router Updated!"
echo "---------------------------------------------------"
echo "👉 You can now call GET /users/contractors/{id} to get the full dashboard data."
echo "---------------------------------------------------"