from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Dict, Any
from app.database import get_db
from app.models import User
from app.core.security import get_current_user
from app.services.whatsapp_service import whatsapp_service

router = APIRouter()

@router.get("/auth-url")
def get_whatsapp_auth_url(
    current_user: User = Depends(get_current_user)
):
    """Get WhatsApp authorization URL"""
    try:
        auth_url = whatsapp_service.get_authorization_url(current_user.id)
        return {
            "auth_url": auth_url,
            "message": "Visit this URL to authorize WhatsApp access"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate auth URL: {str(e)}"
        )

@router.post("/callback")
def handle_whatsapp_callback(
    authorization_code: str = Query(..., description="Authorization code from WhatsApp"),
    state: str = Query(..., description="State parameter containing user info")
):
    """Handle WhatsApp OAuth callback"""
    try:
        user_id = int(state)  # Assuming state contains user_id
        result = whatsapp_service.handle_oauth_callback(authorization_code, user_id)
        
        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to handle callback: {str(e)}"
        )

@router.post("/sync")
def sync_whatsapp_data(
    days: int = Query(30, description="Number of days to sync"),
    current_user: User = Depends(get_current_user)
):
    """Sync WhatsApp data for the user"""
    try:
        result = whatsapp_service.sync_whatsapp_data(current_user.id, days)
        
        return {
            "message": f"Successfully synced WhatsApp data",
            "messages_count": result["messages_count"],
            "providers_found": result["providers_found"],
            "days_synced": result["days_synced"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync WhatsApp data: {str(e)}"
        )

@router.get("/status")
def get_whatsapp_status(
    current_user: User = Depends(get_current_user)
):
    """Check WhatsApp connection status"""
    try:
        access_token = whatsapp_service.get_access_token(current_user.id)
        
        if access_token:
            return {
                "connected": True,
                "message": "WhatsApp is connected and ready"
            }
        else:
            return {
                "connected": False,
                "message": "WhatsApp is not connected"
            }
    except Exception as e:
        return {
            "connected": False,
            "message": f"Error checking WhatsApp status: {str(e)}"
        }

@router.post("/test-connection")
def test_whatsapp_connection(
    current_user: User = Depends(get_current_user)
):
    """Test WhatsApp connection by fetching recent messages"""
    try:
        messages = whatsapp_service.fetch_messages(current_user.id, 7)  # Last 7 days
        
        return {
            "success": True,
            "message": f"Successfully connected to WhatsApp. Found {len(messages)} messages in the last week.",
            "sample_messages": messages[:3] if messages else []  # Return first 3 as sample
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test WhatsApp connection: {str(e)}"
        )
