from fastapi import APIRouter, HTTPException, status, Query, UploadFile, File, Form
from app.database import db
from app.schemas import DiscussionResponse, CommentCreate
from app.services.llm import analyze_complaints
from app.utils.s3 import upload_file_to_s3
from datetime import datetime, timedelta, timezone
import random
from bson import ObjectId

router = APIRouter(prefix="/community", tags=["Community Discussion"])

# --- CONSTANTS ---
IST = timezone(timedelta(hours=5, minutes=30))

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

# --- 1. POST A DISCUSSION (With Optional Image) ---
@router.post("/discuss", status_code=status.HTTP_201_CREATED)
async def post_discussion(
    content: str = Form(..., description="Content of the discussion"),
    category: str = Form("General", description="Category of the post"),
    image: UploadFile = File(None, description="Optional image upload"),
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
                {"$set": {"anonymous_identity": display_name}}
            )
    else:
        # Officials always use Real Name
        display_name = f"Official {user['name']}"

    # --- HANDLE IMAGE UPLOAD ---
    image_url = None
    if image:
        # Use existing S3 utility (stored in same bucket, separate folder for tidiness)
        image_url = upload_file_to_s3(image.file, image.filename, folder="community")

    new_post = {
        "village_name": village_name,
        "user_name": display_name,
        "user_role": role,
        "real_user_id": str(user["_id"]),
        "content": content,
        "category": category,
        "image_url": image_url,  # Save URL to DB
        "status": "Open",
        "replies": [],
        "created_at": datetime.now(IST), # <--- IST TIMESTAMP
        "upvotes": 0,
        "upvoters": [] # Track who has upvoted
    }
    
    result = await db.discussions.insert_one(new_post)
    
    return {
        "message": "Posted successfully", 
        "assigned_identity": display_name, 
        "village": village_name,
        "image_url": image_url,
        "id": str(result.inserted_id)
    }

# --- 2. UPVOTE A DISCUSSION (Toggle) ---
@router.patch("/{discussion_id}/upvote")
async def upvote_discussion(
    discussion_id: str,
    user_id: str = Query(..., description="ID of the user upvoting")
):
    # 1. Validate User
    user, role, error = await get_user_details(user_id)
    if error:
        raise HTTPException(status_code=404, detail=error)
    
    # 2. Validate Discussion
    try:
        oid = ObjectId(discussion_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid Discussion ID")

    discussion = await db.discussions.find_one({"_id": oid})
    if not discussion:
        raise HTTPException(status_code=404, detail="Discussion not found")

    # 3. Check Village Match (Must be same village)
    if discussion["village_name"] != user["village_name"]:
         raise HTTPException(status_code=403, detail="You can only upvote discussions in your own village")

    # 4. TOGGLE UPVOTE LOGIC
    user_oid = str(user["_id"])
    upvoters = discussion.get("upvoters", [])

    if user_oid in upvoters:
        # User already upvoted -> REMOVE UPVOTE
        await db.discussions.update_one(
            {"_id": oid},
            {
                "$inc": {"upvotes": -1},
                "$pull": {"upvoters": user_oid}
            }
        )
        new_count = discussion.get("upvotes", 0) - 1
        return {"message": "Upvote removed", "upvotes": new_count if new_count >= 0 else 0}
    
    else:
        # User hasn't upvoted -> ADD UPVOTE
        await db.discussions.update_one(
            {"_id": oid},
            {
                "$inc": {"upvotes": 1},
                "$push": {"upvoters": user_oid}
            }
        )
        return {"message": "Upvoted successfully", "upvotes": discussion.get("upvotes", 0) + 1}


# --- 3. ADD A COMMENT (Reply) ---
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
                {"$set": {"anonymous_identity": display_name}}
            )
    else:
        display_name = f"Official {user['name']}"

    # 3. Create Reply Object
    reply_obj = {
        "user_name": display_name,
        "user_role": role,
        "content": comment.content,
        "created_at": datetime.now(IST) # <--- IST TIMESTAMP
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

# --- 4. GET VILLAGE FEED ---
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
            replies=clean_replies,
            image_url=d.get("image_url")
        ))
    return results

# --- 5. ANALYZE & INSIGHTS ---
@router.post("/analyze")
async def trigger_analysis():
    last_week = datetime.now(IST) - timedelta(days=7) # <--- IST TIMESTAMP
    posts = await db.discussions.find({"created_at": {"$gte": last_week}}).to_list(100)
    
    if not posts: return {"message": "No data"}
    
    text_data = "\n".join([f"- [{p['category']}] {p['content']}" for p in posts])
    analysis = await analyze_complaints(text_data)
    
    if not analysis: raise HTTPException(status_code=500, detail="AI Failed")

    insight = {
        "period_start": last_week,
        "period_end": datetime.now(IST), # <--- IST TIMESTAMP
        "generated_at": datetime.now(IST), # <--- IST TIMESTAMP
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

# --- 6. RAG SYSTEM ENDPOINTS (Free HF) ---
from app.services.rag_service import sync_discussions_to_vector_db, generate_smart_summary
from pydantic import BaseModel

class RagQuery(BaseModel):
    query: str

@router.post("/rag/sync", tags=["RAG AI"])
async def sync_knowledge_base():
    """
    Re-builds the AI memory from current discussions.
    """
    return await sync_discussions_to_vector_db()

@router.post("/rag/ask", tags=["RAG AI"])
async def ask_village_data(request: RagQuery):
    """
    Ask the AI about village issues.
    """
    answer = await generate_smart_summary(request.query)
    return {"answer": answer}

@router.get("/rag/major-issues", tags=["RAG AI"])
async def get_major_issues_report():
    """
    Auto-generates a report on Major Problems.
    """
    query = "Summarize the top 3 most critical recurring problems in the village and suggest 1 action for each."
    answer = await generate_smart_summary(query)
    return {"report": answer}
