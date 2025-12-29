from fastapi import FastAPI
from app.database import db

app = FastAPI(title="Gram-Sahayak API", version="1.0.0")

@app.get("/")
async def root():
    return {"message": "Welcome to Gram-Sahayak Backend Intelligence"}

@app.get("/health")
async def health_check():
    try:
        # Simple ping to check DB connection
        await db.command("ping")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
