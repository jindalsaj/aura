from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String)  # Full name from Google
    picture = Column(String)  # Profile picture URL from Google
    hashed_password = Column(String)  # Optional for OAuth users
    google_id = Column(String, unique=True, index=True)  # Google user ID
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    properties = relationship("Property", back_populates="owner")
    data_sources = relationship("DataSource", back_populates="user")
    expenses = relationship("Expense", back_populates="user")
    documents = relationship("Document", back_populates="user")

class Property(Base):
    __tablename__ = "properties"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    address = Column(Text, nullable=False)
    property_type = Column(String)  # apartment, house, condo, etc.
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    owner = relationship("User", back_populates="properties")
    expenses = relationship("Expense", back_populates="property")
    documents = relationship("Document", back_populates="property")

class ServiceProvider(Base):
    __tablename__ = "service_providers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    contact_info = Column(JSON)  # phone, email, address
    provider_type = Column(String)  # plumber, electrician, cleaner, etc.
    last_used = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    expenses = relationship("Expense", back_populates="service_provider")

class DataSource(Base):
    __tablename__ = "data_sources"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    source_type = Column(String, nullable=False)  # gmail, whatsapp, bank, drive
    access_token = Column(Text)  # encrypted
    refresh_token = Column(Text)  # encrypted
    is_active = Column(Boolean, default=True)
    last_sync = Column(DateTime(timezone=True))
    sync_status = Column(String, default='idle')  # idle, syncing, completed, error
    sync_progress = Column(Integer, default=0)  # 0-100
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="data_sources")

class Expense(Base):
    __tablename__ = "expenses"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    property_id = Column(Integer, ForeignKey("properties.id"))
    service_provider_id = Column(Integer, ForeignKey("service_providers.id"))
    amount = Column(Float, nullable=False)
    description = Column(Text)
    category = Column(String)  # rent, utilities, maintenance, insurance, etc.
    transaction_date = Column(DateTime(timezone=True), nullable=False)
    source = Column(String)  # bank, manual, receipt
    external_id = Column(String)  # transaction ID from bank, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="expenses")
    property = relationship("Property", back_populates="expenses")
    service_provider = relationship("ServiceProvider", back_populates="expenses")

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    property_id = Column(Integer, ForeignKey("properties.id"))
    title = Column(String, nullable=False)
    document_type = Column(String)  # receipt, contract, insurance, etc.
    source = Column(String)  # gmail, drive, manual
    file_path = Column(String)  # S3 path or local path
    file_type = Column(String)  # pdf, jpg, png, etc.
    content = Column(Text)  # extracted text content
    meta_data = Column(JSON)  # additional metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="documents")
    property = relationship("Property", back_populates="documents")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    source = Column(String, nullable=False)  # gmail, whatsapp
    external_id = Column(String)  # message ID from source
    sender = Column(String)
    recipient = Column(String)
    content = Column(Text, nullable=False)
    message_date = Column(DateTime(timezone=True), nullable=False)
    participants = Column(JSON)  # list of participants
    meta_data = Column(JSON)  # additional metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User")

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_name = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User")
    messages = relationship("ChatMessage", back_populates="session")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(String, nullable=False)  # user, assistant
    content = Column(Text, nullable=False)
    meta_data = Column(JSON)  # sources, confidence, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    session = relationship("ChatSession", back_populates="messages")
