from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import User, ChatSession, ChatMessage
from app.schemas import (
    ChatQuery, 
    ChatResponse, 
    ChatSessionCreate, 
    ChatSession as ChatSessionSchema,
    ChatMessage as ChatMessageSchema
)
from app.core.security import get_current_user

router = APIRouter()

@router.post("/sessions", response_model=ChatSessionSchema)
def create_chat_session(
    session: ChatSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_session = ChatSession(
        user_id=current_user.id,
        session_name=session.session_name
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

@router.get("/sessions", response_model=List[ChatSessionSchema])
def get_chat_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    sessions = db.query(ChatSession).filter(ChatSession.user_id == current_user.id).all()
    return sessions

@router.get("/sessions/{session_id}", response_model=ChatSessionSchema)
def get_chat_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    return session

@router.post("/query", response_model=ChatResponse)
def chat_query(
    query: ChatQuery,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # TODO: Implement LLM integration and query processing
    # For now, return a placeholder response
    
    # Create user message
    if query.session_id:
        user_message = ChatMessage(
            session_id=query.session_id,
            role="user",
            content=query.message
        )
        db.add(user_message)
        db.commit()
    
    # Placeholder response (will be replaced with actual LLM integration)
    response = ChatResponse(
        response="I understand you're asking about your properties and expenses. I'm still learning about your data. Please connect your data sources to get started!",
        sources=[],
        confidence=0.0
    )
    
    # Create assistant message
    if query.session_id:
        assistant_message = ChatMessage(
            session_id=query.session_id,
            role="assistant",
            content=response.response,
            meta_data={"sources": response.sources, "confidence": response.confidence}
        )
        db.add(assistant_message)
        db.commit()
    
    return response

@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageSchema])
def get_chat_messages(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify session belongs to user
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.created_at).all()
    return messages
