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