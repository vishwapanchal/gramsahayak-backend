from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional

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
    password: str
    role: str = "government_official"
# ... (keep existing models) ...

from datetime import datetime

# --- Community Discussion Models ---
class DiscussionCreate(BaseModel):
    content: str
    category: str = "General"  # e.g., Water, Roads, Electricity (User selects this)
    is_anonymous: bool = False

class DiscussionResponse(BaseModel):
    id: str
    user_name: str
    content: str
    category: str
    created_at: datetime
    upvotes: int

# --- AI Insight Models ---
class InsightCreate(BaseModel):
    period_start: datetime
    period_end: datetime
    summary: str
    top_issues: list[str]
    sentiment_score: float  # -1 (Negative) to +1 (Positive)
    suggested_actions: list[str]

class InsightResponse(InsightCreate):
    id: str
    generated_at: datetime
# --- User Response Schemas (Added by setup_users_api.sh) ---
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
    role: str

# --- Project Schemas (Added by setup_projects.sh) ---
class ProjectCreate(BaseModel):
    project_name: str
    description: str
    category: str  # e.g., Water, Roads, Sanitation
    location: str
    contractor_name: str
    contractor_id: str
    contractor_address: str
    allocated_budget: float
    approved_by: str
    start_date: datetime
    due_date: datetime
    status: str = "Pending"  # Pending, In Progress, Completed, Halted
    images: list[str] = []   # URLs to images

class ProjectResponse(ProjectCreate):
    id: str
    created_at: datetime
    milestones: list[str] = [] # e.g., ["Tender Passed", "Foundation Laid"]

# --- UPDATED Project Schemas (With village_name) ---
class ProjectCreate(BaseModel):
    project_name: str
    description: str
    category: str
    village_name: str  # <--- New Field
    location: str      # e.g., "Ward 4, Near School"
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

# --- Dashboard Schemas (Added by setup_dashboard.sh) ---
class DashboardStats(BaseModel):
    budget_used: float        # Card 1: Money spent in village
    issues_resolved: int      # Card 2: Total village issues fixed
    village_mood: str         # Card 3: Happy/Neutral/Angry
    personal_impact: int      # Card 4: Issues YOU helped fix
    next_meeting: str         # Extra: Date of next Gram Sabha
