from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Dict, Any
from app.database import get_db
from app.models import User
from app.core.security import get_current_user
from app.services.drive_service import drive_service

router = APIRouter()

@router.get("/auth-url")
def get_drive_auth_url(
    current_user: User = Depends(get_current_user)
):
    """Get Google Drive OAuth2 authorization URL"""
    try:
        auth_url = drive_service.get_authorization_url(current_user.id)
        return {
            "auth_url": auth_url,
            "message": "Visit this URL to authorize Google Drive access"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate auth URL: {str(e)}"
        )

@router.post("/callback")
def handle_drive_callback(
    authorization_response: str = Query(..., description="Authorization response from Google"),
    state: str = Query(..., description="State parameter containing user info")
):
    """Handle Google Drive OAuth2 callback"""
    try:
        result = drive_service.handle_oauth_callback(authorization_response, state)
        
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
def sync_drive_data(
    days: int = Query(30, description="Number of days to sync"),
    current_user: User = Depends(get_current_user)
):
    """Sync Google Drive data for the user"""
    try:
        # Fetch files
        files = drive_service.fetch_recent_files(current_user.id, days)
        
        # Store in database
        drive_service.store_files_in_db(current_user.id, files)
        
        # Count property-related documents
        property_related = sum(1 for f in files 
                             if drive_service.categorize_document(f['name'], '')['is_property_related'])
        
        return {
            "message": f"Successfully synced {len(files)} files",
            "files_count": len(files),
            "property_related_count": property_related,
            "days_synced": days
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync Google Drive data: {str(e)}"
        )

@router.get("/status")
def get_drive_status(
    current_user: User = Depends(get_current_user)
):
    """Check Google Drive connection status"""
    try:
        credentials = drive_service.get_credentials(current_user.id)
        
        if credentials:
            return {
                "connected": True,
                "message": "Google Drive is connected and ready"
            }
        else:
            return {
                "connected": False,
                "message": "Google Drive is not connected"
            }
    except Exception as e:
        return {
            "connected": False,
            "message": f"Error checking Google Drive status: {str(e)}"
        }

@router.post("/test-connection")
def test_drive_connection(
    current_user: User = Depends(get_current_user)
):
    """Test Google Drive connection by fetching recent files"""
    try:
        files = drive_service.fetch_recent_files(current_user.id, 7)  # Last 7 days
        
        return {
            "success": True,
            "message": f"Successfully connected to Google Drive. Found {len(files)} files in the last week.",
            "sample_files": files[:3] if files else []  # Return first 3 as sample
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test Google Drive connection: {str(e)}"
        )
