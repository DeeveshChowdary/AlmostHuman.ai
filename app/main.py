import os
from dotenv import load_dotenv
from fastapi import FastAPI
from app.api.routes import router as api_router

# Load environment variables from .env file
load_dotenv()

app = FastAPI(
    title="AlmostHuman.ai API",
    version="0.1.0",
    description="Basic FastAPI project structure"
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")

@app.get("/health", tags=["system"])
def health_check():
    return {"status": "healthy"}
