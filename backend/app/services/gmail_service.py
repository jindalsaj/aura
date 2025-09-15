import base64
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.config import settings
from app.database import get_db
from app.models import User, DataSource, Message, Document
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from email.utils import parsedate_to_datetime
from app.services.relevance_filter import relevance_filter


class GmailService:
    def __init__(self):
        self.SCOPES = [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.modify'
        ]
        self.CLIENT_SECRETS_FILE = 'credentials.json'  # Will be created from env vars
        
    def get_authorization_url(self, user_id: int) -> str:
        """Generate OAuth2 authorization URL for Gmail access"""
        # Check if user already has Gmail tokens from Google OAuth
        db = next(get_db())
        try:
            gmail_source = db.query(DataSource).filter(
                DataSource.user_id == user_id,
                DataSource.source_type == "gmail",
                DataSource.is_active == True
            ).first()
            
            if gmail_source and gmail_source.access_token:
                # User already has Gmail access via Google OAuth
                return "already_connected"
        finally:
            db.close()
        
        # Fallback to separate Gmail OAuth if needed
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost:3000/auth/gmail/callback"]
                }
            },
            scopes=self.SCOPES,
            redirect_uri="http://localhost:3000/auth/gmail/callback"
        )
        
        # Add state parameter to identify user
        flow.state = json.dumps({"user_id": user_id})
        
        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        
        return authorization_url
    
    def handle_oauth_callback(self, authorization_response: str, state: str) -> Dict[str, Any]:
        """Handle OAuth2 callback and store credentials"""
        try:
            state_data = json.loads(state)
            user_id = state_data["user_id"]
            
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": settings.GOOGLE_CLIENT_ID,
                        "client_secret": settings.GOOGLE_CLIENT_SECRET,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": ["http://localhost:3000/auth/gmail/callback"]
                    }
                },
                scopes=self.SCOPES,
                redirect_uri="http://localhost:3000/auth/gmail/callback"
            )
            
            flow.fetch_token(authorization_response=authorization_response)
            credentials = flow.credentials
            
            # Store credentials in database
            db = next(get_db())
            try:
                data_source = db.query(DataSource).filter(
                    DataSource.user_id == user_id,
                    DataSource.source_type == 'gmail'
                ).first()
                
                if data_source:
                    data_source.access_token = credentials.token
                    data_source.refresh_token = credentials.refresh_token
                    data_source.is_active = True
                else:
                    data_source = DataSource(
                        user_id=user_id,
                        source_type='gmail',
                        access_token=credentials.token,
                        refresh_token=credentials.refresh_token,
                        is_active=True
                    )
                    db.add(data_source)
                
                db.commit()
                
                return {
                    "success": True,
                    "message": "Gmail connected successfully",
                    "data_source_id": data_source.id
                }
            finally:
                db.close()
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to connect Gmail: {str(e)}"
            }
    
    def get_credentials(self, user_id: int) -> Optional[Credentials]:
        """Get stored credentials for user"""
        db = next(get_db())
        try:
            data_source = db.query(DataSource).filter(
                DataSource.user_id == user_id,
                DataSource.source_type == 'gmail',
                DataSource.is_active == True
            ).first()
            
            if not data_source or not data_source.access_token:
                return None
            
            credentials = Credentials(
                token=data_source.access_token,
                refresh_token=data_source.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                scopes=self.SCOPES
            )
            
            # Refresh token if needed
            if credentials.expired and credentials.refresh_token:
                try:
                    credentials.refresh(Request())
                    
                    # Update stored token
                    data_source.access_token = credentials.token
                    if credentials.refresh_token:
                        data_source.refresh_token = credentials.refresh_token
                    db.commit()
                except Exception as refresh_error:
                    print(f"Error refreshing token: {refresh_error}")
                    # Mark as inactive if refresh fails
                    data_source.is_active = False
                    db.commit()
                    return None
            
            return credentials
        except Exception as e:
            print(f"Error getting credentials: {e}")
            return None
        finally:
            db.close()
    
    def get_service(self, user_id: int):
        """Get Gmail service instance for user"""
        credentials = self.get_credentials(user_id)
        if not credentials:
            raise Exception("Gmail not connected or credentials expired")
        
        return build('gmail', 'v1', credentials=credentials)
    
    def fetch_recent_emails(self, user_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """Fetch emails from the last N days"""
        try:
            service = self.get_service(user_id)
            
            # Calculate date range
            after_date = (datetime.now() - timedelta(days=days)).strftime('%Y/%m/%d')
            query = f'after:{after_date}'
            
            # Get message list
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=100
            ).execute()
            
            messages = results.get('messages', [])
            email_data = []
            
            for msg in messages:
                try:
                    # Get full message details
                    message = service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='full'
                    ).execute()
                    
                    # Extract email data
                    email_info = self._extract_email_data(message)
                    email_data.append(email_info)
                    
                except HttpError as e:
                    print(f"Error fetching message {msg['id']}: {e}")
                    continue
            
            return email_data
            
        except Exception as e:
            print(f"Error fetching emails: {e}")
            return []
    
    def fetch_emails_with_attachments(self, user_id: int) -> List[Dict[str, Any]]:
        """Fetch emails that have attachments"""
        try:
            creds = self.get_credentials(user_id)
            if not creds:
                return []
            
            service = build('gmail', 'v1', credentials=creds)
            
            # Build query for emails with attachments
            query = 'in:inbox has:attachment'
            
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=200  # More results for attachments
            ).execute()
            
            messages = results.get('messages', [])
            email_data = []
            
            for msg in messages:
                try:
                    # Get full message details
                    message = service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='full'
                    ).execute()
                    
                    # Extract email data
                    email_info = self._extract_email_data(message)
                    email_data.append(email_info)
                    
                except HttpError as e:
                    print(f"Error fetching message {msg['id']}: {e}")
                    continue
            
            return email_data
            
        except Exception as e:
            print(f"Error fetching emails with attachments: {e}")
            return []
    
    def _extract_email_data(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant data from Gmail message"""
        payload = message['payload']
        headers = payload.get('headers', [])
        
        # Extract headers
        email_data = {
            'id': message['id'],
            'thread_id': message['threadId'],
            'subject': '',
            'from': '',
            'to': '',
            'date': '',
            'body': '',
            'attachments': []
        }
        
        # Parse headers
        for header in headers:
            name = header['name'].lower()
            value = header['value']
            
            if name == 'subject':
                email_data['subject'] = value
            elif name == 'from':
                email_data['from'] = value
            elif name == 'to':
                email_data['to'] = value
            elif name == 'date':
                email_data['date'] = value
        
        # Extract body
        email_data['body'] = self._extract_body(payload)
        
        # Extract attachments
        email_data['attachments'] = self._extract_attachments(payload)
        
        return email_data
    
    def _extract_body(self, payload: Dict[str, Any]) -> str:
        """Extract email body text"""
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data')
                    if data:
                        body += base64.urlsafe_b64decode(data).decode('utf-8')
                elif part['mimeType'] == 'text/html':
                    data = part['body'].get('data')
                    if data:
                        # For now, just use HTML as text. In production, you'd want to strip HTML
                        body += base64.urlsafe_b64decode(data).decode('utf-8')
        else:
            # Single part message
            if payload['mimeType'] == 'text/plain':
                data = payload['body'].get('data')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
        
        return body
    
    def _extract_attachments(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract attachment information"""
        attachments = []
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['filename']:
                    attachment = {
                        'filename': part['filename'],
                        'mime_type': part['mimeType'],
                        'size': part['body'].get('size', 0),
                        'attachment_id': part['body'].get('attachmentId')
                    }
                    attachments.append(attachment)
        
        return attachments
    
    def download_attachment(self, user_id: int, message_id: str, attachment_id: str) -> bytes:
        """Download attachment content"""
        service = self.get_service(user_id)
        
        attachment = service.users().messages().attachments().get(
            userId='me',
            messageId=message_id,
            id=attachment_id
        ).execute()
        
        data = attachment['data']
        return base64.urlsafe_b64decode(data)
    
    def _parse_email_date(self, date_str: str) -> datetime:
        """Parse email date string from Gmail API"""
        try:
            # Gmail returns dates in RFC 2822 format
            # Use email.utils.parsedate_to_datetime for proper parsing
            return parsedate_to_datetime(date_str)
        except (ValueError, TypeError) as e:
            print(f"Error parsing date '{date_str}': {e}")
            # Fallback to current time if parsing fails
            return datetime.now()
    
    def store_emails_in_db(self, user_id: int, emails: List[Dict[str, Any]]):
        """Store fetched emails in database"""
        db = next(get_db())
        try:
            for email_data in emails:
                # Check if message already exists
                existing = db.query(Message).filter(
                    Message.user_id == user_id,
                    Message.external_id == email_data['id'],
                    Message.source == 'gmail'
                ).first()
                
                if existing:
                    continue
                
                # Create message record
                message = Message(
                    user_id=user_id,
                    source='gmail',
                    external_id=email_data['id'],
                    sender=email_data['from'],
                    recipient=email_data['to'],
                    content=email_data['body'],
                    message_date=self._parse_email_date(email_data['date']) if email_data['date'] else datetime.now(),
                    meta_data={
                        'subject': email_data['subject'],
                        'thread_id': email_data['thread_id'],
                        'attachments': email_data['attachments']
                    }
                )
                
                db.add(message)
                
                # Create document records for attachments
                for attachment in email_data['attachments']:
                    if attachment['size'] > 0:  # Only store non-empty attachments
                        document = Document(
                            user_id=user_id,
                            title=attachment['filename'],
                            document_type='email_attachment',
                            source='gmail',
                            file_type=attachment['mime_type'],
                            meta_data={
                                'message_id': email_data['id'],
                                'attachment_id': attachment['attachment_id'],
                                'size': attachment['size']
                            }
                        )
                        db.add(document)
            
            db.commit()
            
        except Exception as e:
            db.rollback()
            print(f"Error storing emails: {e}")
        finally:
            db.close()
    
    async def sync_emails(self, user_id: int, days_back: Optional[int] = None, attachments_only: bool = False):
        """Sync emails for a user with various options"""
        try:
            print(f"Starting Gmail sync for user {user_id} - days_back: {days_back}, attachments_only: {attachments_only}")
            
            # Get user's Gmail data source
            db = next(get_db())
            try:
                data_source = db.query(DataSource).filter(
                    DataSource.user_id == user_id,
                    DataSource.source_type == 'gmail',
                    DataSource.is_active == True
                ).first()
                
                if not data_source:
                    print(f"No active Gmail data source found for user {user_id}")
                    return
                
                # Update sync status
                data_source.sync_status = 'syncing'
                data_source.sync_progress = 10
                db.commit()
                
                # Fetch emails based on options
                if attachments_only:
                    emails = self.fetch_emails_with_attachments(user_id)
                elif days_back:
                    emails = self.fetch_recent_emails(user_id, days=days_back)
                else:
                    emails = self.fetch_recent_emails(user_id, days=365)  # All emails
                
                data_source.sync_progress = 50
                db.commit()
                
                # Filter emails for property relevance
                print(f"Filtering {len(emails)} emails for property relevance...")
                relevant_emails = await relevance_filter.filter_emails_for_properties(user_id, emails)
                print(f"Found {len(relevant_emails)} property-relevant emails")
                
                # Store only relevant emails
                self.store_emails_in_db(user_id, relevant_emails)
                data_source.sync_progress = 90
                db.commit()
                
                # Update sync status to completed
                data_source.sync_status = 'completed'
                data_source.sync_progress = 100
                data_source.last_sync = func.now()
                db.commit()
                
                print(f"Gmail sync completed for user {user_id} - {len(emails)} emails synced")
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"Gmail sync error for user {user_id}: {e}")
            # Update sync status to error
            try:
                db = next(get_db())
                data_source = db.query(DataSource).filter(
                    DataSource.user_id == user_id,
                    DataSource.source_type == 'gmail',
                    DataSource.is_active == True
                ).first()
                if data_source:
                    data_source.sync_status = 'error'
                    db.commit()
                db.close()
            except:
                pass
    
    def sync_emails_sync(self, user_id: int, days_back: Optional[int] = None, attachments_only: bool = False):
        """Synchronous wrapper for sync_emails to be used with background tasks"""
        import asyncio
        asyncio.run(self.sync_emails(user_id, days_back, attachments_only))


# Global instance
gmail_service = GmailService()
