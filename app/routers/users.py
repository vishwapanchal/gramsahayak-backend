from fastapi import APIRouter, HTTPException, status
from app.database import db
from app.schemas import VillagerResponse, ContractorResponse, OfficialResponse
from typing import List

router = APIRouter(prefix="/users", tags=["User Management"])

# ==========================
# 1. FETCH ALL USERS
# ==========================

@router.get("/villagers", response_model=List[VillagerResponse])
async def get_all_villagers():
    """Fetch all registered villagers"""
    users = await db.villagers.find().to_list(1000)
    for user in users:
        user["id"] = str(user["_id"])
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
    """Fetch all registered government officials"""
    users = await db.government_officials.find().to_list(1000)
    for user in users:
        user["id"] = str(user["_id"])
    return users

# ==========================
# 2. FETCH SINGLE USER
# ==========================

@router.get("/villagers/{phone_number}", response_model=VillagerResponse)
async def get_villager_by_phone(phone_number: str):
    """Fetch a single villager by their Phone Number"""
    user = await db.villagers.find_one({"phone_number": phone_number})
    if not user:
        raise HTTPException(status_code=404, detail="Villager not found")
    
    user["id"] = str(user["_id"])
    return user

@router.get("/contractors/{contractor_id}", response_model=ContractorResponse)
async def get_contractor_by_id(contractor_id: str):
    """Fetch a single contractor by their Contractor ID (e.g., CNT001)"""
    user = await db.contractors.find_one({"contractor_id": contractor_id})
    if not user:
        raise HTTPException(status_code=404, detail="Contractor not found")
    
    user["id"] = str(user["_id"])
    return user

@router.get("/officials/{government_id}", response_model=OfficialResponse)
async def get_official_by_id(government_id: str):
    """Fetch a single official by their Government ID (e.g., GOV001)"""
    user = await db.government_officials.find_one({"government_id": government_id})
    if not user:
        raise HTTPException(status_code=404, detail="Official not found")
    
    user["id"] = str(user["_id"])
    return user
