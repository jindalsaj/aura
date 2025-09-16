import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import plaid
from plaid.api import plaid_api
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
from plaid.configuration import Configuration
from plaid.api_client import ApiClient

from app.core.config import settings
from app.database import get_db
from app.models import User, DataSource, Expense
from sqlalchemy.orm import Session


class PlaidService:
    def __init__(self):
        # Map environment string to Plaid environment
        env_map = {
            'sandbox': plaid.Environment.Sandbox,
            'development': plaid.Environment.Development,
            'production': plaid.Environment.Production
        }
        
        self.configuration = Configuration(
            host=env_map.get(settings.PLAID_ENV, plaid.Environment.Sandbox),
            api_key={
                'clientId': settings.PLAID_CLIENT_ID,
                'secret': settings.PLAID_SECRET
            }
        )
        self.api_client = ApiClient(self.configuration)
        self.client = plaid_api.PlaidApi(self.api_client)
    
    def create_link_token(self, user_id: int) -> Dict[str, Any]:
        """Create a link token for Plaid Link initialization"""
        try:
            request = LinkTokenCreateRequest(
                products=['transactions'],
                client_name='Aura Personal Assistant',
                country_codes=['US'],
                language='en',
                user=LinkTokenCreateRequestUser(
                    client_user_id=str(user_id)
                ),
                webhook='https://your-webhook-url.com/plaid/webhook'  # Update with your webhook
            )
            
            response = self.client.link_token_create(request)
            
            return {
                "success": True,
                "link_token": response['link_token'],
                "expiration": response['expiration']
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to create link token: {str(e)}"
            }
    
    def exchange_public_token(self, user_id: int, public_token: str) -> Dict[str, Any]:
        """Exchange public token for access token"""
        try:
            request = ItemPublicTokenExchangeRequest(
                public_token=public_token
            )
            
            response = self.client.item_public_token_exchange(request)
            access_token = response['access_token']
            item_id = response['item_id']
            
            # Store access token in database
            db = next(get_db())
            try:
                data_source = db.query(DataSource).filter(
                    DataSource.user_id == user_id,
                    DataSource.source_type == 'bank'
                ).first()
                
                if data_source:
                    data_source.access_token = access_token
                    data_source.is_active = True
                    data_source.meta_data = {
                        'item_id': item_id,
                        'connected_at': datetime.now().isoformat()
                    }
                else:
                    data_source = DataSource(
                        user_id=user_id,
                        source_type='bank',
                        access_token=access_token,
                        is_active=True,
                        meta_data={
                            'item_id': item_id,
                            'connected_at': datetime.now().isoformat()
                        }
                    )
                    db.add(data_source)
                
                db.commit()
                
                return {
                    "success": True,
                    "message": "Bank account connected successfully",
                    "data_source_id": data_source.id,
                    "item_id": item_id
                }
            finally:
                db.close()
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to exchange public token: {str(e)}"
            }
    
    def get_access_token(self, user_id: int) -> Optional[str]:
        """Get stored access token for user"""
        db = next(get_db())
        try:
            data_source = db.query(DataSource).filter(
                DataSource.user_id == user_id,
                DataSource.source_type == 'bank',
                DataSource.is_active == True
            ).first()
            
            return data_source.access_token if data_source else None
        finally:
            db.close()
    
    def get_accounts(self, user_id: int) -> List[Dict[str, Any]]:
        """Get user's bank accounts"""
        access_token = self.get_access_token(user_id)
        if not access_token:
            raise Exception("Bank account not connected")
        
        try:
            request = AccountsGetRequest(access_token=access_token)
            response = self.client.accounts_get(request)
            
            accounts = []
            for account in response['accounts']:
                accounts.append({
                    'account_id': account['account_id'],
                    'name': account['name'],
                    'type': account['type'],
                    'subtype': account['subtype'],
                    'mask': account['mask'],
                    'balance': {
                        'available': account['balances'].get('available'),
                        'current': account['balances'].get('current'),
                        'limit': account['balances'].get('limit')
                    }
                })
            
            return accounts
            
        except Exception as e:
            raise Exception(f"Failed to get accounts: {str(e)}")
    
    def get_transactions(self, user_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """Get transactions from the last N days"""
        access_token = self.get_access_token(user_id)
        if not access_token:
            raise Exception("Bank account not connected")
        
        try:
            # Calculate date range
            start_date = (datetime.now() - timedelta(days=days)).date()
            end_date = datetime.now().date()
            
            request = TransactionsGetRequest(
                access_token=access_token,
                start_date=start_date,
                end_date=end_date,
                options=TransactionsGetRequestOptions(
                    count=500,  # Maximum transactions to fetch
                    offset=0
                )
            )
            
            response = self.client.transactions_get(request)
            
            transactions = []
            for transaction in response['transactions']:
                transactions.append({
                    'transaction_id': transaction['transaction_id'],
                    'account_id': transaction['account_id'],
                    'amount': transaction['amount'],
                    'date': transaction['date'].isoformat(),
                    'name': transaction['name'],
                    'merchant_name': transaction.get('merchant_name'),
                    'category': transaction.get('category', []),
                    'category_id': transaction.get('category_id'),
                    'account_owner': transaction.get('account_owner'),
                    'pending': transaction.get('pending', False),
                    'transaction_type': transaction.get('transaction_type'),
                    'location': transaction.get('location', {}),
                    'payment_meta': transaction.get('payment_meta', {})
                })
            
            return transactions
            
        except Exception as e:
            raise Exception(f"Failed to get transactions: {str(e)}")
    
    def categorize_transaction(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Categorize transaction for property management"""
        name = transaction['name'].lower()
        merchant = transaction.get('merchant_name', '').lower()
        categories = transaction.get('category', [])
        
        # Property-related categories
        property_categories = {
            'rent': ['rent', 'lease', 'apartment', 'housing'],
            'utilities': ['electric', 'gas', 'water', 'internet', 'cable', 'phone', 'utility'],
            'maintenance': ['repair', 'maintenance', 'plumber', 'electrician', 'contractor'],
            'insurance': ['insurance', 'premium'],
            'property_tax': ['tax', 'property tax', 'real estate'],
            'hoa': ['hoa', 'homeowners association', 'condo fee'],
            'cleaning': ['cleaning', 'housekeeping', 'maid'],
            'pest_control': ['pest', 'exterminator'],
            'landscaping': ['landscaping', 'lawn', 'garden', 'yard']
        }
        
        # Check for property-related transactions
        for category, keywords in property_categories.items():
            for keyword in keywords:
                if keyword in name or keyword in merchant:
                    return {
                        'category': category,
                        'is_property_related': True,
                        'confidence': 0.8
                    }
        
        # Check categories from Plaid
        if categories:
            for category in categories:
                if any(prop_cat in category.lower() for prop_cat in property_categories.keys()):
                    return {
                        'category': category,
                        'is_property_related': True,
                        'confidence': 0.6
                    }
        
        return {
            'category': 'other',
            'is_property_related': False,
            'confidence': 0.0
        }
    
    def store_transactions_in_db(self, user_id: int, transactions: List[Dict[str, Any]]):
        """Store transactions in database"""
        db = next(get_db())
        try:
            for transaction_data in transactions:
                # Check if transaction already exists
                existing = db.query(Expense).filter(
                    Expense.user_id == user_id,
                    Expense.external_id == transaction_data['transaction_id'],
                    Expense.source == 'bank'
                ).first()
                
                if existing:
                    continue
                
                # Categorize transaction
                categorization = self.categorize_transaction(transaction_data)
                
                # Create expense record
                expense = Expense(
                    user_id=user_id,
                    amount=abs(transaction_data['amount']),  # Store as positive amount
                    description=transaction_data['name'],
                    category=categorization['category'],
                    transaction_date=datetime.fromisoformat(transaction_data['date']),
                    source='bank',
                    external_id=transaction_data['transaction_id'],
                    meta_data={
                        'account_id': transaction_data['account_id'],
                        'merchant_name': transaction_data.get('merchant_name'),
                        'plaid_categories': transaction_data.get('category', []),
                        'is_property_related': categorization['is_property_related'],
                        'confidence': categorization['confidence'],
                        'pending': transaction_data.get('pending', False),
                        'location': transaction_data.get('location', {}),
                        'payment_meta': transaction_data.get('payment_meta', {})
                    }
                )
                
                db.add(expense)
            
            db.commit()
            
        except Exception as e:
            db.rollback()
            print(f"Error storing transactions: {e}")
        finally:
            db.close()


# Global instance
plaid_service = PlaidService()
