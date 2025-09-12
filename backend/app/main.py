from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
import uvicorn

from app.database import get_db, engine
from app.models import Base
from app.routers import auth, properties, data_sources, chat, gmail, plaid, whatsapp, drive, entity_extraction
from app.core.config import settings

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Aura Personal Assistant API",
    description="Personal Home & Property Assistant AI",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(properties.router, prefix="/api/properties", tags=["properties"])
app.include_router(data_sources.router, prefix="/api/data-sources", tags=["data-sources"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(gmail.router, prefix="/api/gmail", tags=["gmail"])
app.include_router(plaid.router, prefix="/api/plaid", tags=["plaid"])
app.include_router(whatsapp.router, prefix="/api/whatsapp", tags=["whatsapp"])
app.include_router(drive.router, prefix="/api/drive", tags=["drive"])
app.include_router(entity_extraction.router, prefix="/api/entities", tags=["entity-extraction"])

@app.get("/")
async def root():
    return {"message": "Aura Personal Assistant API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
