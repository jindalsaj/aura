import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from app.core.config import settings
from app.database import get_db
from app.models import User, DataSource, Message, ServiceProvider
from sqlalchemy.orm import Session


class WhatsAppService:
    def __init__(self):
        self.base_url = "https://graph.facebook.com/v18.0"
        self.access_token = settings.WHATSAPP_ACCESS_TOKEN
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
    
    def get_authorization_url(self, user_id: int) -> str:
        """Generate authorization URL for WhatsApp Business API"""
        # Note: WhatsApp Business API requires business verification
        # This is a placeholder for the actual OAuth flow
        return f"https://business.whatsapp.com/oauth/authorize?client_id={settings.WHATSAPP_ACCESS_TOKEN}&redirect_uri=http://localhost:3000/auth/whatsapp/callback&state={user_id}"
    
    def handle_oauth_callback(self, authorization_code: str, user_id: int) -> Dict[str, Any]:
        """Handle OAuth callback and store credentials"""
        try:
            # Exchange authorization code for access token
            # This is a simplified version - actual implementation would depend on WhatsApp's OAuth flow
            
            # For now, we'll store the access token directly
            # In production, you'd exchange the code for a proper access token
            
            db = next(get_db())
            try:
                data_source = db.query(DataSource).filter(
                    DataSource.user_id == user_id,
                    DataSource.source_type == 'whatsapp'
                ).first()
                
                if data_source:
                    data_source.access_token = settings.WHATSAPP_ACCESS_TOKEN
                    data_source.is_active = True
                    data_source.meta_data = {
                        'phone_number_id': self.phone_number_id,
                        'connected_at': datetime.now().isoformat()
                    }
                else:
                    data_source = DataSource(
                        user_id=user_id,
                        source_type='whatsapp',
                        access_token=settings.WHATSAPP_ACCESS_TOKEN,
                        is_active=True,
                        meta_data={
                            'phone_number_id': self.phone_number_id,
                            'connected_at': datetime.now().isoformat()
                        }
                    )
                    db.add(data_source)
                
                db.commit()
                
                return {
                    "success": True,
                    "message": "WhatsApp connected successfully",
                    "data_source_id": data_source.id
                }
            finally:
                db.close()
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to connect WhatsApp: {str(e)}"
            }
    
    def get_access_token(self, user_id: int) -> Optional[str]:
        """Get stored access token for user"""
        db = next(get_db())
        try:
            data_source = db.query(DataSource).filter(
                DataSource.user_id == user_id,
                DataSource.source_type == 'whatsapp',
                DataSource.is_active == True
            ).first()
            
            return data_source.access_token if data_source else None
        finally:
            db.close()
    
    def fetch_messages(self, user_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """Fetch messages from WhatsApp Business API"""
        access_token = self.get_access_token(user_id)
        if not access_token:
            raise Exception("WhatsApp not connected")
        
        try:
            # Calculate date range
            since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%dT%H:%M:%S')
            
            # Get messages from WhatsApp Business API
            url = f"{self.base_url}/{self.phone_number_id}/messages"
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            params = {
                'since': since,
                'limit': 100
            }
            
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            messages = data.get('data', [])
            
            # Process messages
            processed_messages = []
            for message in messages:
                processed_messages.append({
                    'id': message.get('id'),
                    'from': message.get('from'),
                    'to': message.get('to'),
                    'timestamp': message.get('timestamp'),
                    'type': message.get('type'),
                    'text': message.get('text', {}).get('body', ''),
                    'context': message.get('context', {}),
                    'metadata': {
                        'message_type': message.get('type'),
                        'status': message.get('status'),
                        'pricing': message.get('pricing', {})
                    }
                })
            
            return processed_messages
            
        except requests.RequestException as e:
            raise Exception(f"Failed to fetch WhatsApp messages: {str(e)}")
    
    def extract_service_providers(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract potential service providers from messages"""
        providers = []
        phone_numbers = set()
        
        for message in messages:
            from_number = message.get('from')
            text = message.get('text', '').lower()
            
            if from_number and from_number not in phone_numbers:
                phone_numbers.add(from_number)
                
                # Look for service provider keywords
                service_keywords = {
                    'plumber': ['plumber', 'plumbing', 'pipe', 'leak', 'drain'],
                    'electrician': ['electrician', 'electrical', 'wiring', 'outlet', 'circuit'],
                    'contractor': ['contractor', 'construction', 'renovation', 'repair'],
                    'cleaner': ['cleaner', 'cleaning', 'housekeeping', 'maid'],
                    'landscaper': ['landscaper', 'landscaping', 'lawn', 'garden', 'yard'],
                    'pest_control': ['pest', 'exterminator', 'bug', 'rodent'],
                    'hvac': ['hvac', 'heating', 'cooling', 'air conditioning', 'furnace'],
                    'appliance_repair': ['appliance', 'repair', 'washer', 'dryer', 'refrigerator'],
                    'locksmith': ['locksmith', 'lock', 'key'],
                    'painter': ['painter', 'painting', 'paint']
                }
                
                detected_services = []
                for service_type, keywords in service_keywords.items():
                    if any(keyword in text for keyword in keywords):
                        detected_services.append(service_type)
                
                if detected_services:
                    providers.append({
                        'phone_number': from_number,
                        'services': detected_services,
                        'last_message': text[:100],  # First 100 chars
                        'message_count': 1  # Will be updated if we see more messages
                    })
        
        # Count messages per provider
        for provider in providers:
            phone = provider['phone_number']
            provider['message_count'] = sum(1 for msg in messages if msg.get('from') == phone)
        
        return providers
    
    def store_messages_in_db(self, user_id: int, messages: List[Dict[str, Any]]):
        """Store WhatsApp messages in database"""
        db = next(get_db())
        try:
            for message_data in messages:
                # Check if message already exists
                existing = db.query(Message).filter(
                    Message.user_id == user_id,
                    Message.external_id == message_data['id'],
                    Message.source == 'whatsapp'
                ).first()
                
                if existing:
                    continue
                
                # Create message record
                message = Message(
                    user_id=user_id,
                    source='whatsapp',
                    external_id=message_data['id'],
                    sender=message_data['from'],
                    recipient=message_data['to'],
                    content=message_data['text'],
                    message_date=datetime.fromtimestamp(int(message_data['timestamp'])),
                    participants=[message_data['from'], message_data['to']],
                    meta_data=message_data['metadata']
                )
                
                db.add(message)
            
            db.commit()
            
        except Exception as e:
            db.rollback()
            print(f"Error storing WhatsApp messages: {e}")
        finally:
            db.close()
    
    def store_service_providers_in_db(self, user_id: int, providers: List[Dict[str, Any]]):
        """Store extracted service providers in database"""
        db = next(get_db())
        try:
            for provider_data in providers:
                # Check if provider already exists
                existing = db.query(ServiceProvider).filter(
                    ServiceProvider.contact_info['phone'].astext == provider_data['phone_number']
                ).first()
                
                if existing:
                    # Update last used date and services
                    existing.last_used = datetime.now()
                    if provider_data['services']:
                        existing.provider_type = provider_data['services'][0]  # Primary service
                    continue
                
                # Create new service provider
                provider = ServiceProvider(
                    name=f"Provider {provider_data['phone_number'][-4:]}",  # Use last 4 digits as name
                    contact_info={
                        'phone': provider_data['phone_number'],
                        'whatsapp': True
                    },
                    provider_type=provider_data['services'][0] if provider_data['services'] else 'unknown',
                    last_used=datetime.now()
                )
                
                db.add(provider)
            
            db.commit()
            
        except Exception as e:
            db.rollback()
            print(f"Error storing service providers: {e}")
        finally:
            db.close()
    
    def sync_whatsapp_data(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Sync WhatsApp data and extract service providers"""
        try:
            # Fetch messages
            messages = self.fetch_messages(user_id, days)
            
            # Store messages
            self.store_messages_in_db(user_id, messages)
            
            # Extract service providers
            providers = self.extract_service_providers(messages)
            
            # Store service providers
            self.store_service_providers_in_db(user_id, providers)
            
            return {
                "messages_count": len(messages),
                "providers_found": len(providers),
                "days_synced": days
            }
            
        except Exception as e:
            raise Exception(f"Failed to sync WhatsApp data: {str(e)}")


# Global instance
whatsapp_service = WhatsAppService()
