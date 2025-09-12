from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from app.database import get_db
from app.models import User
from app.schemas import (
    UserCreate, 
    User as UserSchema, 
    Token, 
    GoogleAuthRequest,
    GoogleUserInfo
)
from app.core.security import (
    verify_password, 
    get_password_hash, 
    create_access_token,
    get_current_user
)
from app.core.config import settings
from app.services.google_oauth_service import GoogleOAuthService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
google_oauth_service = GoogleOAuthService()

@router.get("/google/auth-url")
def get_google_auth_url(redirect_uri: str):
    """Get Google OAuth authorization URL"""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth not configured"
        )
    
    auth_url = google_oauth_service.get_auth_url(redirect_uri)
    return {"auth_url": auth_url}

@router.post("/google/callback", response_model=Token)
async def google_callback(auth_request: GoogleAuthRequest, db: Session = Depends(get_db)):
    """Handle Google OAuth callback"""
    try:
        logger.info(f"OAuth callback received - Code: {auth_request.code[:20]}..., Redirect URI: {auth_request.redirect_uri}")
        
        # Exchange code for token
        token_data = await google_oauth_service.exchange_code_for_token(
            auth_request.code, 
            auth_request.redirect_uri
        )
        
        if not token_data:
            logger.error("Token exchange failed - no token data returned")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange code for token"
            )
        
        logger.info("Token exchange successful")
        
        # Get user info from Google
        user_info = await google_oauth_service.get_user_info(token_data["access_token"])
        
        if not user_info:
            logger.error("Failed to get user info from Google")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user information"
            )
        
        logger.info(f"User info retrieved - Email: {user_info.email}, Google ID: {user_info.id}")
        
        # Check if user exists
        logger.info("Checking if user exists in database...")
        db_user = db.query(User).filter(User.google_id == user_info.id).first()
        
        if not db_user:
            logger.info("User not found by Google ID, checking by email...")
            # Check if user exists with same email
            db_user = db.query(User).filter(User.email == user_info.email).first()
            
            if db_user:
                logger.info("User found by email, updating with Google ID...")
                # Update existing user with Google ID
                db_user.google_id = user_info.id
                db_user.name = user_info.name
                db_user.picture = user_info.picture
            else:
                logger.info("Creating new user...")
                # Create new user
                db_user = User(
                    email=user_info.email,
                    name=user_info.name,
                    picture=user_info.picture,
                    google_id=user_info.id,
                    hashed_password=None  # No password for OAuth users
                )
                db.add(db_user)
        else:
            logger.info("User found by Google ID, updating info...")
            # Update user info
            db_user.name = user_info.name
            db_user.picture = user_info.picture
        
        # Store Google OAuth tokens for Gmail and Drive access
        from app.models import DataSource
        
        # Store Gmail tokens
        gmail_source = db.query(DataSource).filter(
            DataSource.user_id == db_user.id,
            DataSource.source_type == "gmail"
        ).first()
        
        if gmail_source:
            gmail_source.access_token = token_data["access_token"]
            gmail_source.refresh_token = token_data.get("refresh_token")
            gmail_source.is_active = True
        else:
            gmail_source = DataSource(
                user_id=db_user.id,
                source_type="gmail",
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                is_active=True
            )
            db.add(gmail_source)
        
        # Store Google Drive tokens
        drive_source = db.query(DataSource).filter(
            DataSource.user_id == db_user.id,
            DataSource.source_type == "drive"
        ).first()
        
        if drive_source:
            drive_source.access_token = token_data["access_token"]
            drive_source.refresh_token = token_data.get("refresh_token")
            drive_source.is_active = True
        else:
            drive_source = DataSource(
                user_id=db_user.id,
                source_type="drive",
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                is_active=True
            )
            db.add(drive_source)
        
        logger.info("Committing database changes...")
        db.commit()
        db.refresh(db_user)
        
        # Create access token
        logger.info("Creating access token...")
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": db_user.email}, expires_delta=access_token_expires
        )
        
        logger.info("Authentication successful!")
        return {"access_token": access_token, "token_type": "bearer"}
        
    except Exception as e:
        logger.error(f"Google OAuth callback error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )

# Keep traditional login for backward compatibility (optional)
@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not user.hashed_password or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserSchema)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user
