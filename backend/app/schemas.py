from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    picture: Optional[str] = None

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    google_id: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Google OAuth schemas
class GoogleUserInfo(BaseModel):
    id: str
    email: str
    name: str
    picture: Optional[str] = None

class GoogleAuthRequest(BaseModel):
    code: str
    state: Optional[str] = None
    redirect_uri: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str

# Property schemas
class PropertyBase(BaseModel):
    name: str
    address: str
    property_type: Optional[str] = None

class PropertyCreate(PropertyBase):
    pass

class Property(PropertyBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PropertyUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    property_type: Optional[str] = None

# Onboarding schemas
class OnboardingPropertiesRequest(BaseModel):
    properties: List[PropertyCreate]

class OnboardingServicesRequest(BaseModel):
    selected_services: List[str]
    gmail_sync_option: Optional[str] = "last_30_days"
    drive_selected_items: Optional[List[str]] = []

class OnboardingSyncRequest(BaseModel):
    properties: List[PropertyCreate]
    selected_services: List[str]
    gmail_sync_option: Optional[str] = "last_30_days"
    drive_selected_items: Optional[List[str]] = []

# Data source schemas
class DataSourceBase(BaseModel):
    source_type: str

class DataSourceCreate(DataSourceBase):
    access_token: str
    refresh_token: Optional[str] = None

class DataSource(DataSourceBase):
    id: int
    user_id: int
    is_active: bool
    last_sync: Optional[datetime] = None
    sync_status: str
    sync_progress: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Chat schemas
class ChatQuery(BaseModel):
    message: str
    session_id: Optional[int] = None

class ChatResponse(BaseModel):
    response: str
    sources: Optional[List[Dict[str, Any]]] = None
    confidence: Optional[float] = None

class ChatSessionCreate(BaseModel):
    session_name: Optional[str] = None

class ChatSession(BaseModel):
    id: int
    user_id: int
    session_name: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ChatMessage(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    meta_data: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Expense schemas
class ExpenseBase(BaseModel):
    amount: float
    description: Optional[str] = None
    category: Optional[str] = None
    transaction_date: datetime
    source: Optional[str] = None

class ExpenseCreate(ExpenseBase):
    property_id: Optional[int] = None
    service_provider_id: Optional[int] = None

class Expense(ExpenseBase):
    id: int
    user_id: int
    property_id: Optional[int] = None
    service_provider_id: Optional[int] = None
    external_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Document schemas
class DocumentBase(BaseModel):
    title: str
    document_type: Optional[str] = None
    source: Optional[str] = None
    file_type: Optional[str] = None
    content: Optional[str] = None

class DocumentCreate(DocumentBase):
    property_id: Optional[int] = None
    file_path: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = None

class Document(DocumentBase):
    id: int
    user_id: int
    property_id: Optional[int] = None
    file_path: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Message schemas
class MessageBase(BaseModel):
    source: str
    external_id: Optional[str] = None
    sender: Optional[str] = None
    recipient: Optional[str] = None
    content: str
    message_date: datetime

class MessageCreate(MessageBase):
    participants: Optional[List[str]] = None
    meta_data: Optional[Dict[str, Any]] = None

class Message(MessageBase):
    id: int
    user_id: int
    participants: Optional[List[str]] = None
    meta_data: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Sync status schemas
class SyncStatus(BaseModel):
    source_type: str
    status: str  # idle, syncing, completed, error
    progress: int  # 0-100
    last_sync: Optional[datetime] = None
    error_message: Optional[str] = None

class SyncStatusResponse(BaseModel):
    services: List[SyncStatus]
    overall_status: str
    overall_progress: int