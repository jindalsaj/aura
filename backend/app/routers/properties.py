from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import User, Property
from app.schemas import PropertyCreate, Property as PropertySchema
from app.core.security import get_current_user

router = APIRouter()

@router.post("/", response_model=PropertySchema)
def create_property(
    property: PropertyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_property = Property(
        name=property.name,
        address=property.address,
        property_type=property.property_type,
        user_id=current_user.id
    )
    db.add(db_property)
    db.commit()
    db.refresh(db_property)
    return db_property

@router.get("/", response_model=List[PropertySchema])
def get_properties(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    properties = db.query(Property).filter(Property.user_id == current_user.id).all()
    return properties

@router.get("/{property_id}", response_model=PropertySchema)
def get_property(
    property_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    property = db.query(Property).filter(
        Property.id == property_id,
        Property.user_id == current_user.id
    ).first()
    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found"
        )
    return property

@router.put("/{property_id}", response_model=PropertySchema)
def update_property(
    property_id: int,
    property_update: PropertyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    property = db.query(Property).filter(
        Property.id == property_id,
        Property.user_id == current_user.id
    ).first()
    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found"
        )
    
    property.name = property_update.name
    property.address = property_update.address
    property.property_type = property_update.property_type
    
    db.commit()
    db.refresh(property)
    return property

@router.delete("/{property_id}")
def delete_property(
    property_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    property = db.query(Property).filter(
        Property.id == property_id,
        Property.user_id == current_user.id
    ).first()
    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found"
        )
    
    db.delete(property)
    db.commit()
    return {"message": "Property deleted successfully"}
