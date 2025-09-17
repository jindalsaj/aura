import io
import base64
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError

import pytesseract
from PIL import Image
import PyPDF2

from app.core.config import settings
from app.database import get_db
from app.models import User, DataSource, Document
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from app.services.relevance_filter import relevance_filter


class DriveService:
    def __init__(self):
        self.SCOPES = [
            'https://www.googleapis.com/auth/drive.readonly',
            'https://www.googleapis.com/auth/drive.metadata.readonly'
        ]
    
    def get_authorization_url(self, user_id: int) -> str:
        """Generate OAuth2 authorization URL for Google Drive access"""
        # Check if user already has Drive tokens from Google OAuth
        db = next(get_db())
        try:
            drive_source = db.query(DataSource).filter(
                DataSource.user_id == user_id,
                DataSource.source_type == "drive",
                DataSource.is_active == True
            ).first()
            
            if drive_source and drive_source.access_token:
                # User already has Drive access via Google OAuth
                return "already_connected"
        finally:
            db.close()
        
        # Fallback to separate Drive OAuth if needed
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost:3000/auth/drive/callback"]
                }
            },
            scopes=self.SCOPES,
            redirect_uri="http://localhost:3000/auth/drive/callback"
        )
        
        # Add state parameter to identify user
        flow.state = str(user_id)
        
        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        
        return authorization_url
    
    def handle_oauth_callback(self, authorization_response: str, state: str) -> Dict[str, Any]:
        """Handle OAuth2 callback and store credentials"""
        try:
            user_id = int(state)
            
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": settings.GOOGLE_CLIENT_ID,
                        "client_secret": settings.GOOGLE_CLIENT_SECRET,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": ["http://localhost:3000/auth/drive/callback"]
                    }
                },
                scopes=self.SCOPES,
                redirect_uri="http://localhost:3000/auth/drive/callback"
            )
            
            flow.fetch_token(authorization_response=authorization_response)
            credentials = flow.credentials
            
            # Store credentials in database
            db = next(get_db())
            try:
                data_source = db.query(DataSource).filter(
                    DataSource.user_id == user_id,
                    DataSource.source_type == 'drive'
                ).first()
                
                if data_source:
                    data_source.access_token = credentials.token
                    data_source.refresh_token = credentials.refresh_token
                    data_source.is_active = True
                else:
                    data_source = DataSource(
                        user_id=user_id,
                        source_type='drive',
                        access_token=credentials.token,
                        refresh_token=credentials.refresh_token,
                        is_active=True
                    )
                    db.add(data_source)
                
                db.commit()
                
                return {
                    "success": True,
                    "message": "Google Drive connected successfully",
                    "data_source_id": data_source.id
                }
            finally:
                db.close()
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to connect Google Drive: {str(e)}"
            }
    
    def get_credentials(self, user_id: int) -> Optional[Credentials]:
        """Get stored credentials for user"""
        db = next(get_db())
        try:
            data_source = db.query(DataSource).filter(
                DataSource.user_id == user_id,
                DataSource.source_type == 'drive',
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
                credentials.refresh(Request())
                
                # Update stored token
                data_source.access_token = credentials.token
                db.commit()
            
            return credentials
        finally:
            db.close()
    
    def get_service(self, user_id: int):
        """Get Google Drive service instance for user"""
        credentials = self.get_credentials(user_id)
        if not credentials:
            raise Exception("Google Drive not connected or credentials expired")
        
        return build('drive', 'v3', credentials=credentials)
    
    def fetch_recent_files(self, user_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """Fetch files from the last N days"""
        try:
            service = self.get_service(user_id)
            
            # Calculate date range
            after_date = (datetime.now() - timedelta(days=days)).isoformat() + 'Z'
            
            # Query for files modified in the last N days
            query = f"modifiedTime > '{after_date}' and trashed = false"
            
            results = service.files().list(
                q=query,
                fields="nextPageToken, files(id, name, mimeType, size, modifiedTime, createdTime, parents, webViewLink)",
                orderBy="modifiedTime desc",
                pageSize=100
            ).execute()
            
            files = results.get('files', [])
            file_data = []
            
            for file in files:
                file_info = {
                    'id': file['id'],
                    'name': file['name'],
                    'mime_type': file['mimeType'],
                    'size': int(file.get('size', 0)),
                    'modified_time': file['modifiedTime'],
                    'created_time': file['createdTime'],
                    'web_view_link': file.get('webViewLink'),
                    'parents': file.get('parents', [])
                }
                file_data.append(file_info)
            
            return file_data
            
        except Exception as e:
            print(f"Error fetching files: {e}")
            return []
    
    def fetch_selected_files(self, user_id: int, selected_items: List[str]) -> List[Dict[str, Any]]:
        """Fetch specific files and folders from Google Drive"""
        try:
            service = self.get_service(user_id)
            if not service:
                return []
            
            file_data = []
            
            for item_id in selected_items:
                try:
                    # Get file metadata
                    file = service.files().get(
                        fileId=item_id,
                        fields='id,name,mimeType,size,modifiedTime,createdTime,webViewLink,parents'
                    ).execute()
                    
                    file_info = {
                        'id': file['id'],
                        'name': file['name'],
                        'mime_type': file['mimeType'],
                        'size': int(file.get('size', 0)),
                        'modified_time': file['modifiedTime'],
                        'created_time': file['createdTime'],
                        'web_view_link': file.get('webViewLink'),
                        'parents': file.get('parents', [])
                    }
                    file_data.append(file_info)
                    
                    # If it's a folder, fetch its contents
                    if file['mimeType'] == 'application/vnd.google-apps.folder':
                        folder_files = self.fetch_folder_contents(user_id, item_id)
                        file_data.extend(folder_files)
                        
                except HttpError as e:
                    print(f"Error fetching file {item_id}: {e}")
                    continue
            
            return file_data
            
        except Exception as e:
            print(f"Error fetching selected files: {e}")
            return []
    
    def fetch_folder_contents(self, user_id: int, folder_id: str) -> List[Dict[str, Any]]:
        """Fetch contents of a specific folder"""
        try:
            service = self.get_service(user_id)
            if not service:
                return []
            
            results = service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                fields='files(id,name,mimeType,size,modifiedTime,createdTime,webViewLink,parents)',
                pageSize=100
            ).execute()
            
            files = results.get('files', [])
            file_data = []
            
            for file in files:
                file_info = {
                    'id': file['id'],
                    'name': file['name'],
                    'mime_type': file['mimeType'],
                    'size': int(file.get('size', 0)),
                    'modified_time': file['modifiedTime'],
                    'created_time': file['createdTime'],
                    'web_view_link': file.get('webViewLink'),
                    'parents': file.get('parents', [])
                }
                file_data.append(file_info)
            
            return file_data
            
        except Exception as e:
            print(f"Error fetching folder contents: {e}")
            return []
    
    def download_file_content(self, user_id: int, file_id: str) -> bytes:
        """Download file content from Google Drive"""
        try:
            service = self.get_service(user_id)
            
            request = service.files().get_media(fileId=file_id)
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            return file_content.getvalue()
            
        except HttpError as e:
            print(f"Error downloading file {file_id}: {e}")
            return b""
    
    def extract_text_from_file(self, file_content: bytes, mime_type: str, filename: str) -> str:
        """Extract text content from various file types"""
        try:
            if mime_type == 'text/plain':
                return file_content.decode('utf-8')
            
            elif mime_type == 'application/pdf':
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
            
            elif mime_type.startswith('image/'):
                # OCR for images
                image = Image.open(io.BytesIO(file_content))
                text = pytesseract.image_to_string(image)
                return text
            
            elif mime_type in ['application/vnd.google-apps.document', 'application/vnd.google-apps.spreadsheet']:
                # Google Docs/Sheets - would need to export as text/CSV first
                # For now, return empty string
                return ""
            
            else:
                return ""
                
        except Exception as e:
            print(f"Error extracting text from {filename}: {e}")
            return ""
    
    def categorize_document(self, filename: str, content: str) -> Dict[str, Any]:
        """Categorize document based on filename and content"""
        filename_lower = filename.lower()
        content_lower = content.lower()
        
        # Property-related document categories
        categories = {
            'lease_agreement': ['lease', 'rental agreement', 'tenancy'],
            'receipt': ['receipt', 'invoice', 'payment'],
            'contract': ['contract', 'agreement', 'terms'],
            'insurance': ['insurance', 'policy', 'coverage'],
            'utility_bill': ['utility', 'electric', 'gas', 'water', 'internet', 'cable'],
            'maintenance': ['maintenance', 'repair', 'service'],
            'tax_document': ['tax', 'property tax', 'assessment'],
            'hoa_document': ['hoa', 'homeowners association', 'condo'],
            'inspection': ['inspection', 'report', 'assessment'],
            'permit': ['permit', 'license', 'approval']
        }
        
        # Check filename first
        for category, keywords in categories.items():
            if any(keyword in filename_lower for keyword in keywords):
                return {
                    'category': category,
                    'confidence': 0.8,
                    'is_property_related': True
                }
        
        # Check content
        for category, keywords in categories.items():
            if any(keyword in content_lower for keyword in keywords):
                return {
                    'category': category,
                    'confidence': 0.6,
                    'is_property_related': True
                }
        
        return {
            'category': 'other',
            'confidence': 0.0,
            'is_property_related': False
        }
    
    def store_files_in_db(self, user_id: int, files: List[Dict[str, Any]]):
        """Store fetched files in database"""
        db = next(get_db())
        try:
            for file_data in files:
                # Check if document already exists
                existing = db.query(Document).filter(
                    Document.user_id == user_id,
                    Document.metadata['file_id'].astext == file_data['id'],
                    Document.source == 'drive'
                ).first()
                
                if existing:
                    continue
                
                # Download and extract content for text files and PDFs
                content = ""
                if file_data['mime_type'] in ['text/plain', 'application/pdf'] or file_data['mime_type'].startswith('image/'):
                    try:
                        file_content = self.download_file_content(user_id, file_data['id'])
                        content = self.extract_text_from_file(
                            file_content, 
                            file_data['mime_type'], 
                            file_data['name']
                        )
                    except Exception as e:
                        print(f"Error processing file {file_data['name']}: {e}")
                
                # Categorize document
                categorization = self.categorize_document(file_data['name'], content)
                
                # Create document record
                document = Document(
                    user_id=user_id,
                    title=file_data['name'],
                    document_type=categorization['category'],
                    source='drive',
                    file_path=file_data['web_view_link'],  # Store Google Drive link
                    file_type=file_data['mime_type'],
                    content=content,
                    meta_data={
                        'file_id': file_data['id'],
                        'size': file_data['size'],
                        'modified_time': file_data['modified_time'],
                        'created_time': file_data['created_time'],
                        'parents': file_data['parents'],
                        'is_property_related': categorization['is_property_related'],
                        'confidence': categorization['confidence']
                    }
                )
                
                db.add(document)
            
            db.commit()
            
        except Exception as e:
            db.rollback()
            print(f"Error storing files: {e}")
        finally:
            db.close()
    
    async def sync_files(self, user_id: int, selected_items: Optional[List[str]] = None):
        """Sync files for a user with optional item selection"""
        try:
            print(f"Starting Drive sync for user {user_id} - selected_items: {selected_items}")
            
            # Get user's Drive data source
            db = next(get_db())
            try:
                data_source = db.query(DataSource).filter(
                    DataSource.user_id == user_id,
                    DataSource.source_type == 'drive',
                    DataSource.is_active == True
                ).first()
                
                if not data_source:
                    print(f"No active Drive data source found for user {user_id}")
                    return
                
                # Update sync status
                data_source.sync_status = 'syncing'
                data_source.sync_progress = 10
                db.commit()
                
                # Fetch files based on selection
                if selected_items:
                    files = self.fetch_selected_files(user_id, selected_items)
                else:
                    files = self.fetch_recent_files(user_id, days=30)
                
                data_source.sync_progress = 50
                db.commit()
                
                # Filter files for property relevance
                print(f"Filtering {len(files)} files for property relevance...")
                relevant_files = await relevance_filter.filter_documents_for_properties(user_id, files)
                print(f"Found {len(relevant_files)} property-relevant files")
                
                # Store only relevant files
                self.store_files_in_db(user_id, relevant_files)
                data_source.sync_progress = 90
                db.commit()
                
                # Update sync status to completed
                data_source.sync_status = 'completed'
                data_source.sync_progress = 100
                data_source.last_sync = func.now()
                db.commit()
                
                print(f"Drive sync completed for user {user_id} - {len(files)} files synced")
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"Drive sync error for user {user_id}: {e}")
            # Update sync status to error
            try:
                db = next(get_db())
                data_source = db.query(DataSource).filter(
                    DataSource.user_id == user_id,
                    DataSource.source_type == 'drive',
                    DataSource.is_active == True
                ).first()
                if data_source:
                    data_source.sync_status = 'error'
                    db.commit()
                db.close()
            except:
                pass
    
    def sync_files_sync(self, user_id: int, selected_items: Optional[List[str]] = None):
        """Synchronous wrapper for sync_files to be used with background tasks"""
        import asyncio
        asyncio.run(self.sync_files(user_id, selected_items))
    
    def list_drive_items(self, user_id: int) -> List[Dict[str, Any]]:
        """List all files and folders in user's Google Drive"""
        try:
            creds = self.get_credentials(user_id)
            if not creds:
                return []
            
            service = build('drive', 'v3', credentials=creds)
            
            # Get all files and folders
            results = service.files().list(
                pageSize=1000,
                fields="nextPageToken, files(id, name, mimeType, parents, size, modifiedTime, webViewLink)"
            ).execute()
            
            items = results.get('files', [])
            
            # Organize items with folder structure
            drive_items = []
            for item in items:
                # Skip Google-specific files
                if item['name'].startswith('.'):
                    continue
                
                drive_items.append({
                    'id': item['id'],
                    'name': item['name'],
                    'type': 'folder' if item['mimeType'] == 'application/vnd.google-apps.folder' else 'file',
                    'mimeType': item['mimeType'],
                    'size': item.get('size', '0'),
                    'modifiedTime': item.get('modifiedTime', ''),
                    'webViewLink': item.get('webViewLink', ''),
                    'parents': item.get('parents', [])
                })
            
            return drive_items
            
        except Exception as e:
            print(f"Error listing Drive items: {e}")
            return []


# Global instance
drive_service = DriveService()
