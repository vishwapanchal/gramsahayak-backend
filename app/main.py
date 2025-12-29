from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import db
from app.routers import auth, community  # <--- Imported community here
import pymongo

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create indexes to ensure uniqueness (No duplicate phone numbers/IDs)
    await db.villagers.create_index([("phone_number", pymongo.ASCENDING)], unique=True)
    await db.contractors.create_index([("contractor_id", pymongo.ASCENDING)], unique=True)
    await db.government_officials.create_index([("government_id", pymongo.ASCENDING)], unique=True)
    yield

app = FastAPI(title="Gram-Sahayak API", version="1.0.0", lifespan=lifespan)

# Register the Routers
app.include_router(auth.router)
app.include_router(community.router)  # <--- Added this line to activate community endpoints

@app.get("/")
async def root():
    return {"message": "Welcome to Gram-Sahayak Backend Intelligence"}

@app.get("/health")
async def health_check():
    try:
        await db.command("ping")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}