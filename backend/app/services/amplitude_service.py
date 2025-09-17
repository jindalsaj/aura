import httpx
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class AmplitudeService:
    def __init__(self):
        self.api_key = settings.AMPLITUDE_API_KEY
        self.endpoint = "https://api2.amplitude.com/2/httpapi"
    
    def _generate_device_id(self, user_id: Optional[str] = None) -> str:
        """Generate a device ID for tracking"""
        if user_id:
            # Use user_id as base for consistent device ID
            return f"user_{user_id}_{uuid.uuid4().hex[:8]}"
        return str(uuid.uuid4())
    
    async def track_event(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        device_id: Optional[str] = None,
        event_properties: Optional[Dict[str, Any]] = None,
        user_properties: Optional[Dict[str, Any]] = None,
        insert_id: Optional[str] = None
    ) -> bool:
        """
        Track an event to Amplitude
        
        Args:
            event_type: The name of the event
            user_id: User identifier
            device_id: Device identifier (will be generated if not provided)
            event_properties: Properties specific to this event
            user_properties: Properties about the user
            insert_id: Unique identifier for deduplication
        
        Returns:
            bool: True if event was tracked successfully, False otherwise
        """
        if not self.api_key:
            logger.warning("Amplitude API key not configured, skipping event tracking")
            return False
        
        try:
            # Generate device_id if not provided
            if not device_id:
                device_id = self._generate_device_id(user_id)
            
            # Generate insert_id if not provided for deduplication
            if not insert_id:
                insert_id = str(uuid.uuid4())
            
            # Prepare event data
            event_data = {
                "event_type": event_type,
                "device_id": device_id,
                "time": int(datetime.now().timestamp() * 1000),  # milliseconds since epoch
                "insert_id": insert_id
            }
            
            # Add user_id if provided
            if user_id:
                event_data["user_id"] = user_id
            
            # Add event properties if provided
            if event_properties:
                event_data["event_properties"] = event_properties
            
            # Prepare request payload
            payload = {
                "api_key": self.api_key,
                "events": [event_data]
            }
            
            # Add user properties if provided
            if user_properties:
                payload["user_properties"] = user_properties
            
            # Send request to Amplitude
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.endpoint,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "*/*"
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    logger.info(f"Successfully tracked event: {event_type}")
                    return True
                else:
                    logger.error(f"Failed to track event {event_type}: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error tracking event {event_type}: {e}")
            return False
    
    async def track_google_signin(self, user_id: str, email: str, name: str) -> bool:
        """Track Google sign-in event"""
        return await self.track_event(
            event_type="Google Sign In",
            user_id=user_id,
            event_properties={
                "signin_method": "google",
                "email": email,
                "name": name
            },
            user_properties={
                "email": email,
                "name": name,
                "signin_method": "google",
                "user_email": email  # Additional email field for better tracking
            }
        )
    
    async def track_data_source_sync(
        self, 
        user_id: str, 
        source_type: str, 
        sync_status: str,
        items_count: Optional[int] = None,
        user_email: Optional[str] = None
    ) -> bool:
        """Track data source sync event"""
        event_properties = {
            "source_type": source_type,
            "sync_status": sync_status
        }
        
        if items_count is not None:
            event_properties["items_count"] = items_count
        
        if user_email:
            event_properties["user_email"] = user_email
        
        user_properties = {}
        if user_email:
            user_properties["email"] = user_email
            user_properties["user_email"] = user_email
        
        return await self.track_event(
            event_type="Data Source Sync",
            user_id=user_id,
            event_properties=event_properties,
            user_properties=user_properties if user_properties else None
        )
    
    async def track_page_visit(
        self, 
        user_id: Optional[str], 
        page_name: str, 
        device_id: Optional[str] = None,
        user_email: Optional[str] = None
    ) -> bool:
        """Track page visit event"""
        event_properties = {
            "page_name": page_name,
            "timestamp": datetime.now().isoformat()
        }
        
        if user_email:
            event_properties["user_email"] = user_email
        
        user_properties = {}
        if user_email:
            user_properties["email"] = user_email
            user_properties["user_email"] = user_email
        
        return await self.track_event(
            event_type="Page Visit",
            user_id=user_id,
            device_id=device_id,
            event_properties=event_properties,
            user_properties=user_properties if user_properties else None
        )
    
    async def track_user_registration(self, user_id: str, email: str, name: str) -> bool:
        """Track user registration event"""
        return await self.track_event(
            event_type="User Registration",
            user_id=user_id,
            event_properties={
                "email": email,
                "name": name
            },
            user_properties={
                "email": email,
                "name": name
            }
        )

# Global instance
amplitude_service = AmplitudeService()
