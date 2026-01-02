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
