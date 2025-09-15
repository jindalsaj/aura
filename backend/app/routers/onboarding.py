from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import User, Property, DataSource
from app.schemas import (
    OnboardingPropertiesRequest,
    OnboardingServicesRequest,
    OnboardingSyncRequest,
    Property as PropertySchema,
    SyncStatusResponse,
    SyncStatus
)
from app.core.security import get_current_user
from app.services.gmail_service import gmail_service
from app.services.drive_service import drive_service
from app.services.calendar_service import calendar_service

router = APIRouter()

@router.post("/properties", response_model=List[PropertySchema])
def save_properties(
    request: OnboardingPropertiesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save user properties during onboarding"""
    try:
        # Delete existing properties for this user
        db.query(Property).filter(Property.user_id == current_user.id).delete()
        
        # Create new properties
        saved_properties = []
        for prop_data in request.properties:
            property = Property(
                name=prop_data.name,
                address=prop_data.address,
                property_type=prop_data.property_type,
                user_id=current_user.id
            )
            db.add(property)
            saved_properties.append(property)
        
        db.commit()
        
        # Refresh to get IDs
        for prop in saved_properties:
            db.refresh(prop)
        
        return saved_properties
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save properties: {str(e)}"
        )

@router.post("/services")
def configure_services(
    request: OnboardingServicesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Configure selected services during onboarding"""
    try:
        # Update or create data sources for selected services
        for service_type in request.selected_services:
            # Check if data source already exists
            data_source = db.query(DataSource).filter(
                DataSource.user_id == current_user.id,
                DataSource.source_type == service_type
            ).first()
            
            if not data_source:
                # Create new data source
                data_source = DataSource(
                    user_id=current_user.id,
                    source_type=service_type,
                    is_active=True,
                    sync_status='idle',
                    sync_progress=0
                )
                db.add(data_source)
        
        db.commit()
        
        return {
            "message": "Services configured successfully",
            "selected_services": request.selected_services,
            "gmail_sync_option": request.gmail_sync_option,
            "drive_selected_items": request.drive_selected_items
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to configure services: {str(e)}"
        )

@router.post("/sync")
def start_onboarding_sync(
    request: OnboardingSyncRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start the onboarding sync process"""
    try:
        # Save properties first
        db.query(Property).filter(Property.user_id == current_user.id).delete()
        for prop_data in request.properties:
            property = Property(
                name=prop_data.name,
                address=prop_data.address,
                property_type=prop_data.property_type,
                user_id=current_user.id
            )
            db.add(property)
        
        # Configure data sources
        for service_type in request.selected_services:
            data_source = db.query(DataSource).filter(
                DataSource.user_id == current_user.id,
                DataSource.source_type == service_type
            ).first()
            
            if not data_source:
                data_source = DataSource(
                    user_id=current_user.id,
                    source_type=service_type,
                    is_active=True,
                    sync_status='idle',
                    sync_progress=0
                )
                db.add(data_source)
        
        db.commit()
        
        # Start background sync tasks
        for service_type in request.selected_services:
            if service_type == 'gmail':
                background_tasks.add_task(
                    sync_gmail_with_options,
                    current_user.id,
                    request.gmail_sync_option
                )
            elif service_type == 'drive':
                background_tasks.add_task(
                    sync_drive_with_selection,
                    current_user.id,
                    request.drive_selected_items or []
                )
            elif service_type == 'calendar':
                background_tasks.add_task(
                    sync_calendar_with_range,
                    current_user.id
                )
        
        return {
            "message": "Onboarding sync started",
            "selected_services": request.selected_services,
            "sync_options": {
                "gmail": request.gmail_sync_option,
                "drive_items": request.drive_selected_items,
                "calendar_range": "past_14_days_future"
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start onboarding sync: {str(e)}"
        )

@router.get("/sync/status", response_model=SyncStatusResponse)
def get_sync_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current sync status for all services"""
    try:
        data_sources = db.query(DataSource).filter(
            DataSource.user_id == current_user.id
        ).all()
        
        services = []
        total_progress = 0
        active_syncs = 0
        
        for source in data_sources:
            service_status = SyncStatus(
                source_type=source.source_type,
                status=source.sync_status,
                progress=source.sync_progress,
                last_sync=source.last_sync
            )
            services.append(service_status)
            
            total_progress += source.sync_progress
            if source.sync_status == 'syncing':
                active_syncs += 1
        
        # Calculate overall status
        if active_syncs > 0:
            overall_status = 'syncing'
        elif all(s.status == 'completed' for s in services):
            overall_status = 'completed'
        elif any(s.status == 'error' for s in services):
            overall_status = 'error'
        else:
            overall_status = 'idle'
        
        overall_progress = total_progress // len(services) if services else 0
        
        return SyncStatusResponse(
            services=services,
            overall_status=overall_status,
            overall_progress=overall_progress
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sync status: {str(e)}"
        )

@router.get("/properties", response_model=List[PropertySchema])
def get_user_properties(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's properties"""
    try:
        properties = db.query(Property).filter(
            Property.user_id == current_user.id
        ).all()
        
        return properties
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get properties: {str(e)}"
        )

# Background sync functions
async def sync_gmail_with_options(user_id: int, sync_option: str):
    """Sync Gmail with specific options"""
    try:
        # Update sync status
        from app.database import SessionLocal
        db = SessionLocal()
        
        data_source = db.query(DataSource).filter(
            DataSource.user_id == user_id,
            DataSource.source_type == 'gmail'
        ).first()
        
        if data_source:
            data_source.sync_status = 'syncing'
            data_source.sync_progress = 0
            db.commit()
            
            # Perform sync based on option
            if sync_option == 'all':
                await gmail_service.sync_emails(user_id, days_back=None)
            elif sync_option == 'last_30_days':
                await gmail_service.sync_emails(user_id, days_back=30)
            elif sync_option == 'last_90_days':
                await gmail_service.sync_emails(user_id, days_back=90)
            elif sync_option == 'attachments_only':
                await gmail_service.sync_emails(user_id, attachments_only=True)
            
            # Update completion status
            data_source.sync_status = 'completed'
            data_source.sync_progress = 100
            db.commit()
            
    except Exception as e:
        # Update error status
        if 'data_source' in locals() and data_source:
            data_source.sync_status = 'error'
            db.commit()
        print(f"Gmail sync error: {e}")
    finally:
        if 'db' in locals():
            db.close()

async def sync_drive_with_selection(user_id: int, selected_items: List[str]):
    """Sync Google Drive with selected items"""
    try:
        from app.database import SessionLocal
        db = SessionLocal()
        
        data_source = db.query(DataSource).filter(
            DataSource.user_id == user_id,
            DataSource.source_type == 'drive'
        ).first()
        
        if data_source:
            data_source.sync_status = 'syncing'
            data_source.sync_progress = 0
            db.commit()
            
            # Perform selective sync
            await drive_service.sync_files(user_id, selected_items=selected_items)
            
            # Update completion status
            data_source.sync_status = 'completed'
            data_source.sync_progress = 100
            db.commit()
            
    except Exception as e:
        if 'data_source' in locals() and data_source:
            data_source.sync_status = 'error'
            db.commit()
        print(f"Drive sync error: {e}")
    finally:
        if 'db' in locals():
            db.close()

async def sync_calendar_with_range(user_id: int):
    """Sync Google Calendar with past 14 days and future events"""
    try:
        from app.database import SessionLocal
        db = SessionLocal()
        
        data_source = db.query(DataSource).filter(
            DataSource.user_id == user_id,
            DataSource.source_type == 'calendar'
        ).first()
        
        if data_source:
            data_source.sync_status = 'syncing'
            data_source.sync_progress = 0
            db.commit()
            
            # Perform calendar sync (past 14 days + future)
            await calendar_service.sync_events(user_id, days_back=14, include_future=True)
            
            # Update completion status
            data_source.sync_status = 'completed'
            data_source.sync_progress = 100
            db.commit()
            
    except Exception as e:
        if 'data_source' in locals() and data_source:
            data_source.sync_status = 'error'
            db.commit()
        print(f"Calendar sync error: {e}")
    finally:
        if 'db' in locals():
            db.close()
