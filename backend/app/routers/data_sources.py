from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import User, DataSource
from app.schemas import DataSourceCreate, DataSource as DataSourceSchema
from app.core.security import get_current_user
from app.services.gmail_service import gmail_service
from app.services.drive_service import drive_service

router = APIRouter()

@router.post("/", response_model=DataSourceSchema)
def create_data_source(
    data_source: DataSourceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if user already has this data source type
    existing = db.query(DataSource).filter(
        DataSource.user_id == current_user.id,
        DataSource.source_type == data_source.source_type
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Data source {data_source.source_type} already exists"
        )
    
    db_data_source = DataSource(
        user_id=current_user.id,
        source_type=data_source.source_type,
        access_token=data_source.access_token,
        refresh_token=data_source.refresh_token,
        is_active=data_source.is_active
    )
    db.add(db_data_source)
    db.commit()
    db.refresh(db_data_source)
    return db_data_source

@router.get("/", response_model=List[DataSourceSchema])
def get_data_sources(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    data_sources = db.query(DataSource).filter(DataSource.user_id == current_user.id).all()
    return data_sources

@router.get("/{data_source_id}", response_model=DataSourceSchema)
def get_data_source(
    data_source_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    data_source = db.query(DataSource).filter(
        DataSource.id == data_source_id,
        DataSource.user_id == current_user.id
    ).first()
    if not data_source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data source not found"
        )
    return data_source

@router.put("/{data_source_id}/toggle")
def toggle_data_source(
    data_source_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    data_source = db.query(DataSource).filter(
        DataSource.id == data_source_id,
        DataSource.user_id == current_user.id
    ).first()
    if not data_source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data source not found"
        )
    
    data_source.is_active = not data_source.is_active
    db.commit()
    return {"message": f"Data source {'activated' if data_source.is_active else 'deactivated'}"}

@router.delete("/{data_source_id}")
def delete_data_source(
    data_source_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    data_source = db.query(DataSource).filter(
        DataSource.id == data_source_id,
        DataSource.user_id == current_user.id
    ).first()
    if not data_source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data source not found"
        )
    
    db.delete(data_source)
    db.commit()
    return {"message": "Data source deleted successfully"}

@router.post("/sync/gmail")
def sync_gmail_data(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Sync Gmail data for the current user"""
    # Check if user has Gmail connected
    gmail_source = db.query(DataSource).filter(
        DataSource.user_id == current_user.id,
        DataSource.source_type == "gmail",
        DataSource.is_active == True
    ).first()
    
    if not gmail_source:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gmail not connected or inactive"
        )
    
    # Update sync status to syncing
    gmail_source.sync_status = 'syncing'
    gmail_source.sync_progress = 0
    db.commit()
    
    # Start background sync
    background_tasks.add_task(gmail_service.sync_emails_sync, current_user.id)
    
    return {"message": "Gmail sync started in background"}

@router.post("/sync/drive")
def sync_drive_data(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Sync Google Drive data for the current user"""
    # Check if user has Drive connected
    drive_source = db.query(DataSource).filter(
        DataSource.user_id == current_user.id,
        DataSource.source_type == "drive",
        DataSource.is_active == True
    ).first()
    
    if not drive_source:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google Drive not connected or inactive"
        )
    
    # Update sync status to syncing
    drive_source.sync_status = 'syncing'
    drive_source.sync_progress = 0
    db.commit()
    
    # Start background sync
    background_tasks.add_task(drive_service.sync_files_sync, current_user.id)
    
    return {"message": "Google Drive sync started in background"}

@router.post("/sync/all")
def sync_all_data(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Sync all connected data sources for the current user"""
    # Get all active data sources
    active_sources = db.query(DataSource).filter(
        DataSource.user_id == current_user.id,
        DataSource.is_active == True
    ).all()
    
    if not active_sources:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active data sources found"
        )
    
    # Start background sync for each source
    for source in active_sources:
        if source.source_type == "gmail":
            background_tasks.add_task(gmail_service.sync_emails, current_user.id)
        elif source.source_type == "drive":
            background_tasks.add_task(drive_service.sync_files, current_user.id)
    
    return {"message": f"Sync started for {len(active_sources)} data sources"}

@router.get("/sync/status")
def get_sync_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get sync status for all data sources"""
    data_sources = db.query(DataSource).filter(
        DataSource.user_id == current_user.id,
        DataSource.is_active == True
    ).all()
    
    sync_status = {}
    for source in data_sources:
        sync_status[source.source_type] = {
            "status": source.sync_status,
            "progress": source.sync_progress,
            "last_sync": source.last_sync.isoformat() if source.last_sync else None
        }
    
    return sync_status
