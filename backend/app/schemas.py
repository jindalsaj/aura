from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    picture: Optional[str] = None

class UserCreate(UserBase):
    password: Optional[str] = None
    google_id: Optional[str] = None

class User(UserBase):
    id: int
    google_id: Optional[str] = None
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Google OAuth schemas
class GoogleUserInfo(BaseModel):
    id: str
    email: str
    name: str
    picture: Optional[str] = None
    verified_email: bool = False

class GoogleAuthRequest(BaseModel):
    code: str
    redirect_uri: str

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

# Service Provider schemas
class ServiceProviderBase(BaseModel):
    name: str
    contact_info: Optional[Dict[str, Any]] = None
    provider_type: Optional[str] = None

class ServiceProviderCreate(ServiceProviderBase):
    pass

class ServiceProvider(ServiceProviderBase):
    id: int
    last_used: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Data Source schemas
class DataSourceBase(BaseModel):
    source_type: str
    is_active: bool = True

class DataSourceCreate(DataSourceBase):
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None

class DataSource(DataSourceBase):
    id: int
    user_id: int
    last_sync: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Expense schemas
class ExpenseBase(BaseModel):
    amount: float
    description: Optional[str] = None
    category: Optional[str] = None
    transaction_date: datetime
    source: str
    external_id: Optional[str] = None

class ExpenseCreate(ExpenseBase):
    property_id: Optional[int] = None
    service_provider_id: Optional[int] = None

class Expense(ExpenseBase):
    id: int
    user_id: int
    property_id: Optional[int] = None
    service_provider_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Document schemas
class DocumentBase(BaseModel):
    title: str
    document_type: Optional[str] = None
    source: str
    file_type: Optional[str] = None
    content: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = None

class DocumentCreate(DocumentBase):
    property_id: Optional[int] = None
    file_path: Optional[str] = None

class Document(DocumentBase):
    id: int
    user_id: int
    property_id: Optional[int] = None
    file_path: Optional[str] = None
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
    participants: Optional[List[str]] = None
    meta_data: Optional[Dict[str, Any]] = None

class MessageCreate(MessageBase):
    pass

class Message(MessageBase):
    id: int
    user_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Chat schemas
class ChatMessageBase(BaseModel):
    role: str
    content: str
    meta_data: Optional[Dict[str, Any]] = None

class ChatMessageCreate(ChatMessageBase):
    session_id: int

class ChatMessage(ChatMessageBase):
    id: int
    session_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class ChatSessionBase(BaseModel):
    session_name: Optional[str] = None

class ChatSessionCreate(ChatSessionBase):
    pass

class ChatSession(ChatSessionBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    messages: List[ChatMessage] = []
    
    class Config:
        from_attributes = True

# Authentication schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# Query schemas
class ChatQuery(BaseModel):
    message: str
    session_id: Optional[int] = None

class ChatResponse(BaseModel):
    response: str
    sources: Optional[List[Dict[str, Any]]] = None
    confidence: Optional[float] = None
