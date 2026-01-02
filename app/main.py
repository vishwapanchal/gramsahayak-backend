from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database import db
# Import all routers including complaints
from app.routers import auth, community, users, projects, dashboard, schemes, proposals, complaints
import pymongo
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create Indexes
    await db.villagers.create_index([("phone_number", pymongo.ASCENDING)], unique=True)
    await db.contractors.create_index([("contractor_id", pymongo.ASCENDING)], unique=True)
    await db.government_officials.create_index([("government_id", pymongo.ASCENDING)], unique=True)
    await db.schemes.create_index([("scheme_id", pymongo.ASCENDING)], unique=True)
    yield

app = FastAPI(title="Gram-Sahayak API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(auth.router)
app.include_router(community.router)
app.include_router(users.router)
app.include_router(projects.router)
app.include_router(dashboard.router)
app.include_router(schemes.router)
app.include_router(proposals.router)
app.include_router(complaints.router)

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
