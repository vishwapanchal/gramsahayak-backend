from fastapi import APIRouter, HTTPException, status, Query
from app.database import db
from app.schemas import DiscussionCreate, DiscussionResponse, CommentCreate
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

# --- 0. CLEAR DATA (Utility Route - Optional) ---
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

    # 1. Determine Identity & Village
    village_name = user["village_name"]
    
    if role == "villager":
        display_name = generate_anonymous_name()
    else:
        # Officials show their real name
        display_name = f"Official {user['name']}"

    new_post = {
        "village_name": village_name,  # <--- CRITICAL: Village Filter
        "user_name": display_name,
        "user_role": role,
        "real_user_id": str(user["_id"]),
        "content": post.content,
        "category": post.category,
        "status": "Open",
        "replies": [], # <--- Init empty replies
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

    # 2. Determine Identity
    if role == "villager":
        display_name = generate_anonymous_name()
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
        {"$push": {"replies": reply_obj}}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Discussion not found")

    return {"message": "Comment added", "identity": display_name}

# --- 3. GET VILLAGE FEED (Filtered) ---
@router.get("/feed", response_model=list[DiscussionResponse])
async def get_feed(
    user_id: str = Query(..., description="ID of the logged-in user to fetch THEIR village feed"),
    limit: int = 50
):
    # 1. Get User's Village
    user, role, error = await get_user_details(user_id)
    if error:
        raise HTTPException(status_code=404, detail=error)
        
    village_name = user["village_name"]

    # 2. Fetch Discussions ONLY for this village
    discussions = await db.discussions.find(
        {"village_name": village_name}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    results = []
    for d in discussions:
        # Convert replies if they exist
        clean_replies = []
        if "replies" in d:
            clean_replies = d["replies"]

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
    posts = await db.discussions.find({"created_at": {"": last_week}}).to_list(100)
    
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
