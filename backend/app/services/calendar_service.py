import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import User, DataSource, Message
from app.core.config import settings
from app.services.relevance_filter import relevance_filter
import json

class CalendarService:
    def __init__(self):
        self.scopes = ['https://www.googleapis.com/auth/calendar.readonly']
        self.client_config = {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost:3000/", "/callback", "/auth/callback"]
            }
        }

    def get_authorization_url(self, user_id: int) -> str:
        """Get Google Calendar authorization URL"""
        flow = Flow.from_client_config(
            self.client_config,
            scopes=self.scopes,
            redirect_uri="http://localhost:3000/"
        )
        
        # Add state parameter to identify user
        flow.state = f"calendar_{user_id}"
        
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        
        return auth_url

    def get_credentials(self, user_id: int) -> Optional[Credentials]:
        """Get stored credentials for user"""
        db = SessionLocal()
        try:
            data_source = db.query(DataSource).filter(
                DataSource.user_id == user_id,
                DataSource.source_type == 'calendar'
            ).first()
            
            if not data_source or not data_source.access_token:
                return None
            
            # Create credentials from stored tokens
            creds = Credentials(
                token=data_source.access_token,
                refresh_token=data_source.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                scopes=self.scopes
            )
            
            # Refresh if needed
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                
                # Update stored tokens
                data_source.access_token = creds.token
                if creds.refresh_token:
                    data_source.refresh_token = creds.refresh_token
                db.commit()
            
            return creds
            
        except Exception as e:
            print(f"Error getting calendar credentials: {e}")
            return None
        finally:
            db.close()

    async def sync_events(self, user_id: int, days_back: int = 14, include_future: bool = True) -> Dict[str, Any]:
        """Sync calendar events for a user"""
        db = SessionLocal()
        try:
            # Get or create data source
            data_source = db.query(DataSource).filter(
                DataSource.user_id == user_id,
                DataSource.source_type == 'calendar'
            ).first()
            
            if not data_source:
                raise Exception("Calendar data source not found")
            
            # Update sync status
            data_source.sync_status = 'syncing'
            data_source.sync_progress = 0
            db.commit()
            
            # Get credentials
            creds = self.get_credentials(user_id)
            if not creds:
                raise Exception("No valid calendar credentials")
            
            # Build service
            service = build('calendar', 'v3', credentials=creds)
            
            # Calculate time range
            now = datetime.utcnow()
            time_min = now - timedelta(days=days_back)
            time_max = now + timedelta(days=365) if include_future else now
            
            time_min_str = time_min.isoformat() + 'Z'
            time_max_str = time_max.isoformat() + 'Z'
            
            # Fetch events
            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min_str,
                timeMax=time_max_str,
                maxResults=1000,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Update progress
            data_source.sync_progress = 50
            db.commit()
            
            # Filter events for property relevance
            print(f"Filtering {len(events)} calendar events for property relevance...")
            relevant_events = await relevance_filter.filter_calendar_events_for_properties(user_id, events)
            print(f"Found {len(relevant_events)} property-relevant events")
            
            # Store only relevant events as messages (for consistency with other services)
            stored_count = 0
            for event in relevant_events:
                try:
                    # Extract event details
                    event_id = event.get('id', '')
                    summary = event.get('summary', 'No Title')
                    description = event.get('description', '')
                    start = event.get('start', {})
                    end = event.get('end', {})
                    
                    # Parse start time
                    start_time = None
                    if 'dateTime' in start:
                        start_time = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
                    elif 'date' in start:
                        start_time = datetime.fromisoformat(start['date'] + 'T00:00:00+00:00')
                    
                    # Create event content
                    content = f"Event: {summary}"
                    if description:
                        content += f"\nDescription: {description}"
                    if start_time:
                        content += f"\nStart: {start_time.strftime('%Y-%m-%d %H:%M')}"
                    
                    # Check if event already exists
                    existing = db.query(Message).filter(
                        Message.user_id == user_id,
                        Message.source == 'calendar',
                        Message.external_id == event_id
                    ).first()
                    
                    if not existing:
                        message = Message(
                            user_id=user_id,
                            source='calendar',
                            external_id=event_id,
                            sender='calendar',
                            recipient=user_id,
                            content=content,
                            message_date=start_time or now,
                            meta_data={
                                'event_type': 'calendar_event',
                                'summary': summary,
                                'description': description,
                                'start': start,
                                'end': end,
                                'attendees': event.get('attendees', []),
                                'location': event.get('location', ''),
                                'status': event.get('status', '')
                            }
                        )
                        db.add(message)
                        stored_count += 1
                        
                except Exception as e:
                    print(f"Error storing calendar event: {e}")
                    continue
            
            # Update completion status
            data_source.sync_status = 'completed'
            data_source.sync_progress = 100
            data_source.last_sync = now
            db.commit()
            
            return {
                'status': 'success',
                'events_synced': stored_count,
                'total_events': len(events),
                'time_range': f"{days_back} days back, {'future included' if include_future else 'future excluded'}"
            }
            
        except Exception as e:
            # Update error status
            if 'data_source' in locals() and data_source:
                data_source.sync_status = 'error'
                data_source.sync_progress = 0
                db.commit()
            
            print(f"Calendar sync error: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
        finally:
            db.close()

    def get_recent_events(self, user_id: int, days: int = 7) -> List[Dict[str, Any]]:
        """Get recent calendar events for a user"""
        db = SessionLocal()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            events = db.query(Message).filter(
                Message.user_id == user_id,
                Message.source == 'calendar',
                Message.message_date >= cutoff_date
            ).order_by(Message.message_date.desc()).limit(20).all()
            
            return [
                {
                    'id': event.id,
                    'summary': event.meta_data.get('summary', 'No Title') if event.meta_data else 'No Title',
                    'description': event.meta_data.get('description', '') if event.meta_data else '',
                    'start_time': event.message_date.isoformat(),
                    'location': event.meta_data.get('location', '') if event.meta_data else '',
                    'attendees': event.meta_data.get('attendees', []) if event.meta_data else []
                }
                for event in events
            ]
            
        except Exception as e:
            print(f"Error getting recent calendar events: {e}")
            return []
        finally:
            db.close()
    
    def sync_calendar_events_sync(self, user_id: int):
        """Synchronous wrapper for sync_calendar_events to be used with background tasks"""
        import asyncio
        asyncio.run(self.sync_calendar_events(user_id))

# Create global instance
calendar_service = CalendarService()
