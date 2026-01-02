from fastapi import APIRouter, HTTPException, status, Query, Depends
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

# --- 1. POST A COMPLAINT ---
@router.post("/discuss", status_code=status.HTTP_201_CREATED)
async def post_complaint(
    post: DiscussionCreate, 
    villager_id: str = Query(..., description="The ID of the villager posting this")
):
    try:
        user_obj_id = ObjectId(villager_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid User ID format")

    is_villager = await db.villagers.find_one({"_id": user_obj_id})
    
    if not is_villager:
        if await db.contractors.find_one({"_id": user_obj_id}) or            await db.government_officials.find_one({"_id": user_obj_id}):
            raise HTTPException(status_code=403, detail="Only Villagers can post complaints.")
        raise HTTPException(status_code=404, detail="Villager not found")

    anon_name = generate_anonymous_name()

    new_post = {
        "user_name": anon_name,
        "real_user_id": str(user_obj_id), # We store this to track 'Personal Impact'
        "content": post.content,
        "category": post.category,
        "status": "Open",            # <--- New Status Field
        "created_at": datetime.utcnow(),
        "upvotes": 0
    }
    
    result = await db.discussions.insert_one(new_post)
    
    return {"message": "Complaint posted", "assigned_identity": anon_name, "id": str(result.inserted_id)}

# --- 2. GET FEED (Only shows Open issues) ---
@router.get("/feed", response_model=list[DiscussionResponse])
async def get_feed(limit: int = 20):
    # Only show non-resolved issues in the main feed? Or all? Let's show all.
    discussions = await db.discussions.find().sort("created_at", -1).limit(limit).to_list(limit)
    
    results = []
    for d in discussions:
        results.append(DiscussionResponse(
            id=str(d["_id"]),
            user_name=d["user_name"],
            content=d["content"],
            category=d["category"],
            created_at=d["created_at"],
            upvotes=d["upvotes"]
        ))
    return results

# --- 3. RESOLVE ISSUE (For Officials) ---
@router.patch("/{discussion_id}/resolve")
async def resolve_issue(discussion_id: str):
    """
    Marks a complaint as 'Resolved'. 
    This increases the 'Personal Impact' score of the villager who posted it.
    """
    try:
        obj_id = ObjectId(discussion_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid ID")

    result = await db.discussions.update_one(
        {"_id": obj_id}, 
        {"$set": {"status": "Resolved"}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Discussion not found")
        
    return {"message": "Issue marked as Resolved"}

# --- 4. ANALYZE & INSIGHTS (Existing Logic) ---
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
