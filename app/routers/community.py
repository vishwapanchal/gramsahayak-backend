from fastapi import APIRouter, HTTPException, status, Query
from app.database import db
from app.schemas import DiscussionCreate, DiscussionResponse
from app.services.llm import analyze_complaints
from datetime import datetime, timedelta
import random
from bson import ObjectId

router = APIRouter(prefix="/community", tags=["Community Discussion"])

# --- HELPER: Random Anonymizer ---
ADJECTIVES = ["Silent", "Hidden", "Mystery", "Brave", "Calm", "Wandering", "Happy", "Vocal"]
NOUNS = ["Tiger", "River", "Banyan", "Peacock", "Lotus", "Eagle", "Lion", "Voice"]

def generate_anonymous_name():
    return f"{random.choice(ADJECTIVES)} {random.choice(NOUNS)}"

# --- 1. POST A COMPLAINT (VILLAGERS ONLY) ---
@router.post("/discuss", status_code=status.HTTP_201_CREATED)
async def post_complaint(
    post: DiscussionCreate, 
    villager_id: str = Query(..., description="The ID of the villager posting this")
):
    """
    Only Villagers can post. 
    They are assigned a RANDOM ANONYMOUS NAME automatically.
    """
    # 1. SECURITY CHECK: Is this user actually a villager?
    # Convert string ID to ObjectId
    try:
        user_obj_id = ObjectId(villager_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid User ID format")

    # Check the 'villagers' collection
    is_villager = await db.villagers.find_one({"_id": user_obj_id})
    
    if not is_villager:
        # Check if they are contractor/official to give a specific error
        if await db.contractors.find_one({"_id": user_obj_id}) or \
           await db.government_officials.find_one({"_id": user_obj_id}):
            raise HTTPException(
                status_code=403, 
                detail="Only Villagers can post complaints. Officials/Contractors are observers."
            )
        raise HTTPException(status_code=404, detail="Villager not found")

    # 2. Assign Random Name (Anonymity Logic)
    # We ignore whatever name they have. We give them a mask.
    anon_name = generate_anonymous_name()

    new_post = {
        "user_name": anon_name,  # <--- Random Name Used Here
        "real_user_id": str(user_obj_id), # We keep track internally, but never show it
        "content": post.content,
        "category": post.category,
        "created_at": datetime.utcnow(),
        "upvotes": 0
    }
    
    result = await db.discussions.insert_one(new_post)
    
    return {
        "message": "Complaint posted successfully", 
        "assigned_identity": anon_name, # Tell them their secret name
        "id": str(result.inserted_id)
    }

# --- 2. GET DISCUSSION FEED ---
@router.get("/feed", response_model=list[DiscussionResponse])
async def get_feed(limit: int = 20):
    discussions = await db.discussions.find().sort("created_at", -1).limit(limit).to_list(limit)
    
    results = []
    for d in discussions:
        results.append(DiscussionResponse(
            id=str(d["_id"]),
            user_name=d["user_name"], # This will show "Silent Tiger", not "Ramesh"
            content=d["content"],
            category=d["category"],
            created_at=d["created_at"],
            upvotes=d["upvotes"]
        ))
    return results

# --- 3. TRIGGER AI ANALYSIS ---
@router.post("/analyze", status_code=status.HTTP_200_OK)
async def trigger_analysis():
    # 1. Fetch recent data (Last 7 days)
    last_week = datetime.utcnow() - timedelta(days=7)
    cursor = db.discussions.find({"created_at": {"$gte": last_week}})
    posts = await cursor.to_list(length=100)
    
    if not posts:
        return {"message": "No new discussions to analyze."}

    # 2. Prepare text for LLM
    text_data = "\n".join([f"- [{p['category']}] {p['content']}" for p in posts])

    # 3. Call OpenRouter
    analysis_result = await analyze_complaints(text_data)
    
    if not analysis_result:
        raise HTTPException(status_code=500, detail="AI Analysis failed")

    # 4. Save Insight to DB
    insight_doc = {
        "period_start": last_week,
        "period_end": datetime.utcnow(),
        "generated_at": datetime.utcnow(),
        "summary": analysis_result.get("summary", "No summary"),
        "top_issues": analysis_result.get("top_issues", []),
        "sentiment_score": analysis_result.get("sentiment_score", 0),
        "suggested_actions": analysis_result.get("suggested_actions", [])
    }
    
    await db.insights.insert_one(insight_doc)
    return {"message": "Analysis complete", "insight": insight_doc}

# --- 4. GET INSIGHTS ---
@router.get("/insights/latest")
async def get_latest_insight():
    insight = await db.insights.find_one(sort=[("generated_at", -1)])
    if not insight:
        return {"message": "No insights generated yet."}
    
    insight["id"] = str(insight["_id"])
    del insight["_id"]
    return insight