from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Dict, Any
from app.database import get_db
from app.models import User
from app.core.security import get_current_user
from app.services.gmail_service import gmail_service

router = APIRouter()

@router.get("/auth-url")
def get_gmail_auth_url(
    current_user: User = Depends(get_current_user)
):
    """Get Gmail OAuth2 authorization URL"""
    try:
        auth_url = gmail_service.get_authorization_url(current_user.id)
        return {
            "auth_url": auth_url,
            "message": "Visit this URL to authorize Gmail access"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate auth URL: {str(e)}"
        )

@router.post("/callback")
def handle_gmail_callback(
    authorization_response: str = Query(..., description="Authorization response from Google"),
    state: str = Query(..., description="State parameter containing user info")
):
    """Handle Gmail OAuth2 callback"""
    try:
        result = gmail_service.handle_oauth_callback(authorization_response, state)
        
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
def sync_gmail_data(
    days: int = Query(30, description="Number of days to sync"),
    current_user: User = Depends(get_current_user)
):
    """Sync Gmail data for the user"""
    try:
        # Fetch emails
        emails = gmail_service.fetch_recent_emails(current_user.id, days)
        
        # Store in database
        gmail_service.store_emails_in_db(current_user.id, emails)
        
        return {
            "message": f"Successfully synced {len(emails)} emails",
            "emails_count": len(emails),
            "days_synced": days
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync Gmail data: {str(e)}"
        )

@router.get("/status")
def get_gmail_status(
    current_user: User = Depends(get_current_user)
):
    """Check Gmail connection status"""
    try:
        credentials = gmail_service.get_credentials(current_user.id)
        
        if credentials:
            return {
                "connected": True,
                "message": "Gmail is connected and ready"
            }
        else:
            return {
                "connected": False,
                "message": "Gmail is not connected"
            }
    except Exception as e:
        return {
            "connected": False,
            "message": f"Error checking Gmail status: {str(e)}"
        }

@router.post("/test-connection")
def test_gmail_connection(
    current_user: User = Depends(get_current_user)
):
    """Test Gmail connection by fetching a few recent emails"""
    try:
        emails = gmail_service.fetch_recent_emails(current_user.id, 1)  # Last 1 day
        
        return {
            "success": True,
            "message": f"Successfully connected to Gmail. Found {len(emails)} emails in the last day.",
            "sample_emails": emails[:3] if emails else []  # Return first 3 as sample
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test Gmail connection: {str(e)}"
        )
