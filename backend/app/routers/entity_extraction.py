from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any
from app.database import get_db
from app.models import User
from app.core.security import get_current_user
from app.services.entity_extraction_service import entity_extraction_service

router = APIRouter()

@router.post("/process")
def process_user_data(
    current_user: User = Depends(get_current_user)
):
    """Process all user data to extract entities and relationships"""
    try:
        result = entity_extraction_service.process_user_data(current_user.id)
        
        return {
            "message": "Successfully processed user data",
            "total_entities": result['total_entities'],
            "entities": result['entities']
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process user data: {str(e)}"
        )

@router.get("/entities")
def get_extracted_entities(
    current_user: User = Depends(get_current_user)
):
    """Get all extracted entities for the user"""
    try:
        result = entity_extraction_service.process_user_data(current_user.id)
        
        return {
            "entities": result['entities'],
            "total_entities": result['total_entities']
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get entities: {str(e)}"
        )
