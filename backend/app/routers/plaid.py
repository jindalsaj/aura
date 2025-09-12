from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from app.database import get_db
from app.models import User
from app.core.security import get_current_user
from app.services.plaid_service import plaid_service

router = APIRouter()

@router.get("/link-token")
def create_link_token(
    current_user: User = Depends(get_current_user)
):
    """Create a link token for Plaid Link initialization"""
    try:
        result = plaid_service.create_link_token(current_user.id)
        
        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["message"]
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create link token: {str(e)}"
        )

@router.post("/exchange-token")
def exchange_public_token(
    public_token: str,
    current_user: User = Depends(get_current_user)
):
    """Exchange public token for access token"""
    try:
        result = plaid_service.exchange_public_token(current_user.id, public_token)
        
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
            detail=f"Failed to exchange public token: {str(e)}"
        )

@router.get("/accounts")
def get_accounts(
    current_user: User = Depends(get_current_user)
):
    """Get user's bank accounts"""
    try:
        accounts = plaid_service.get_accounts(current_user.id)
        return {
            "accounts": accounts,
            "count": len(accounts)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get accounts: {str(e)}"
        )

@router.get("/transactions")
def get_transactions(
    days: int = Query(30, description="Number of days to fetch transactions for"),
    current_user: User = Depends(get_current_user)
):
    """Get user's transactions"""
    try:
        transactions = plaid_service.get_transactions(current_user.id, days)
        return {
            "transactions": transactions,
            "count": len(transactions),
            "days": days
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get transactions: {str(e)}"
        )

@router.post("/sync")
def sync_bank_data(
    days: int = Query(30, description="Number of days to sync"),
    current_user: User = Depends(get_current_user)
):
    """Sync bank data for the user"""
    try:
        # Get transactions
        transactions = plaid_service.get_transactions(current_user.id, days)
        
        # Store in database
        plaid_service.store_transactions_in_db(current_user.id, transactions)
        
        # Count property-related transactions
        property_related = sum(1 for t in transactions 
                             if plaid_service.categorize_transaction(t)['is_property_related'])
        
        return {
            "message": f"Successfully synced {len(transactions)} transactions",
            "transactions_count": len(transactions),
            "property_related_count": property_related,
            "days_synced": days
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync bank data: {str(e)}"
        )

@router.get("/status")
def get_bank_status(
    current_user: User = Depends(get_current_user)
):
    """Check bank connection status"""
    try:
        access_token = plaid_service.get_access_token(current_user.id)
        
        if access_token:
            # Test connection by getting accounts
            accounts = plaid_service.get_accounts(current_user.id)
            return {
                "connected": True,
                "message": f"Bank account connected. {len(accounts)} accounts available.",
                "accounts_count": len(accounts)
            }
        else:
            return {
                "connected": False,
                "message": "Bank account is not connected"
            }
    except Exception as e:
        return {
            "connected": False,
            "message": f"Error checking bank status: {str(e)}"
        }

@router.post("/test-connection")
def test_bank_connection(
    current_user: User = Depends(get_current_user)
):
    """Test bank connection by fetching recent transactions"""
    try:
        transactions = plaid_service.get_transactions(current_user.id, 7)  # Last 7 days
        
        return {
            "success": True,
            "message": f"Successfully connected to bank. Found {len(transactions)} transactions in the last week.",
            "sample_transactions": transactions[:3] if transactions else []  # Return first 3 as sample
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test bank connection: {str(e)}"
        )
