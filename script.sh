#!/bin/bash

echo "🚀 Setting up Permanent Anonymous Identities..."

# ==========================================
# 1. Update Schemas (Expose Identity in Profile)
# ==========================================
echo "📝 Updating 'app/schemas.py' to include 'anonymous_identity'..."

cat <<EOF > app/schemas.py
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

# --- User Response Schemas (UPDATED) ---
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
    anonymous_identity: Optional[str] = None  # <--- NEW: Shows their permanent alias

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
EOF

# ==========================================
# 2. Update Community Router (Permanent Identity Logic)
# ==========================================
echo "📝 Rewrite 'app/routers/community.py' with Permanent Identity Logic..."

cat <<EOF > app/routers/community.py
from fastapi import APIRouter, HTTPException, status, Query
from app.database import db
from app.schemas import DiscussionCreate, DiscussionResponse, CommentCreate
from app.services.llm import analyze_complaints
from datetime import datetime, timedelta
import random
from bson import ObjectId

router = APIRouter(prefix="/community", tags=["Community Discussion"])

# --- HELPER: Random Anonymizer ---
ADJECTIVES = ["Silent", "Hidden", "Mystery", "Brave", "Calm", "Wandering", "Happy", "Vocal", "Fast", "Wise"]
NOUNS = ["Tiger", "River", "Banyan", "Peacock", "Lotus", "Eagle", "Lion", "Voice", "Horse", "Bear"]

def generate_anonymous_name():
    return f"{random.choice(ADJECTIVES)} {random.choice(NOUNS)}"

async def get_user_details(user_id: str):
    """
    Identifies if the user is a Villager or Official and returns details.
    """
    try:
        obj_id = ObjectId(user_id)
    except:
        return None, None, "Invalid ID"

    # Check Villager
    villager = await db.villagers.find_one({"_id": obj_id})
    if villager:
        return villager, "villager", None

    # Check Official
    official = await db.government_officials.find_one({"_id": obj_id})
    if official:
        return official, "official", None

    return None, None, "User not found"

# --- 0. CLEAR DATA (Optional) ---
@router.delete("/reset", status_code=200)
async def reset_discussions():
    await db.discussions.delete_many({})
    return {"message": "All discussions cleared."}

# --- 1. POST A DISCUSSION (Filtered by Village) ---
@router.post("/discuss", status_code=status.HTTP_201_CREATED)
async def post_discussion(
    post: DiscussionCreate, 
    user_id: str = Query(..., description="ID of the Villager or Official")
):
    user, role, error = await get_user_details(user_id)
    if error:
        raise HTTPException(status_code=404, detail=error)

    village_name = user["village_name"]
    display_name = ""

    # --- PERMANENT IDENTITY LOGIC ---
    if role == "villager":
        # Check if they already have an alias
        if "anonymous_identity" in user and user["anonymous_identity"]:
            display_name = user["anonymous_identity"]
        else:
            # Generate NEW Permanent Identity
            display_name = generate_anonymous_name()
            # Save it to their profile forever
            await db.villagers.update_one(
                {"_id": user["_id"]},
                {"\$set": {"anonymous_identity": display_name}}
            )
    else:
        # Officials always use Real Name
        display_name = f"Official {user['name']}"

    new_post = {
        "village_name": village_name,
        "user_name": display_name,
        "user_role": role,
        "real_user_id": str(user["_id"]),
        "content": post.content,
        "category": post.category,
        "status": "Open",
        "replies": [],
        "created_at": datetime.utcnow(),
        "upvotes": 0
    }
    
    result = await db.discussions.insert_one(new_post)
    
    return {
        "message": "Posted successfully", 
        "assigned_identity": display_name, 
        "village": village_name,
        "id": str(result.inserted_id)
    }

# --- 2. ADD A COMMENT (Reply) ---
@router.post("/{discussion_id}/comment", status_code=status.HTTP_201_CREATED)
async def add_comment(
    discussion_id: str,
    comment: CommentCreate,
    user_id: str = Query(..., description="ID of the User commenting")
):
    # 1. Validate User
    user, role, error = await get_user_details(user_id)
    if error:
        raise HTTPException(status_code=404, detail=error)

    display_name = ""

    # --- PERMANENT IDENTITY LOGIC (For Comments too) ---
    if role == "villager":
        if "anonymous_identity" in user and user["anonymous_identity"]:
            display_name = user["anonymous_identity"]
        else:
            # If they comment first before posting, assign identity here too
            display_name = generate_anonymous_name()
            await db.villagers.update_one(
                {"_id": user["_id"]},
                {"\$set": {"anonymous_identity": display_name}}
            )
    else:
        display_name = f"Official {user['name']}"

    # 3. Create Reply Object
    reply_obj = {
        "user_name": display_name,
        "user_role": role,
        "content": comment.content,
        "created_at": datetime.utcnow()
    }

    # 4. Update Discussion
    try:
        disc_oid = ObjectId(discussion_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid Discussion ID")

    result = await db.discussions.update_one(
        {"_id": disc_oid},
        {"\$push": {"replies": reply_obj}}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Discussion not found")

    return {"message": "Comment added", "identity": display_name}

# --- 3. GET VILLAGE FEED ---
@router.get("/feed", response_model=list[DiscussionResponse])
async def get_feed(
    user_id: str = Query(..., description="ID of the logged-in user"),
    limit: int = 50
):
    user, role, error = await get_user_details(user_id)
    if error:
        raise HTTPException(status_code=404, detail=error)
        
    village_name = user["village_name"]

    discussions = await db.discussions.find(
        {"village_name": village_name}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    results = []
    for d in discussions:
        clean_replies = d.get("replies", [])
        results.append(DiscussionResponse(
            id=str(d["_id"]),
            village_name=d["village_name"],
            user_name=d["user_name"],
            user_role=d["user_role"],
            content=d["content"],
            category=d["category"],
            created_at=d["created_at"],
            upvotes=d.get("upvotes", 0),
            replies=clean_replies
        ))
    return results

# --- 4. ANALYZE & INSIGHTS ---
@router.post("/analyze")
async def trigger_analysis():
    last_week = datetime.utcnow() - timedelta(days=7)
    posts = await db.discussions.find({"created_at": {"$gte": last_week}}).to_list(100)
    
    if not posts: return {"message": "No data"}
    
    text_data = "\n".join([f"- [{p['category']}] {p['content']}" for p in posts])
    analysis = await analyze_complaints(text_data)
    
    if not analysis: raise HTTPException(status_code=500, detail="AI Failed")

    insight = {
        "period_start": last_week,
        "period_end": datetime.utcnow(),
        "generated_at": datetime.utcnow(),
        "summary": analysis.get("summary", ""),
        "top_issues": analysis.get("top_issues", []),
        "sentiment_score": analysis.get("sentiment_score", 0),
        "suggested_actions": analysis.get("suggested_actions", [])
    }
    await db.insights.insert_one(insight)
    return {"message": "Analysis Done", "insight": insight}

@router.get("/insights/latest")
async def get_latest_insight():
    insight = await db.insights.find_one(sort=[("generated_at", -1)])
    if not insight: return {"message": "No insights"}
    insight["id"] = str(insight["_id"])
    del insight["_id"]
    return insight
EOF

echo "---------------------------------------------------"
echo "✅ SUCCESS: Permanent Identities Configured!"
echo "---------------------------------------------------"
echo "👉 When a villager first posts, they are assigned a name."
echo "   e.g., 'Silent Tiger'"
echo "👉 This name is saved to their profile DB."
echo "👉 All future posts/comments will use this same name."
echo "---------------------------------------------------"
echo "🔄 Please restart your server: ./run_server.sh"