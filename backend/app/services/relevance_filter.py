import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import User, Property, Message, Document
from app.services.llm_service import llm_service

class RelevanceFilter:
    """Service to filter content based on property relevance using LLM"""
    
    def __init__(self):
        self.property_keywords = [
            'property', 'apartment', 'house', 'home', 'rental', 'lease', 'mortgage',
            'landlord', 'tenant', 'rent', 'utilities', 'maintenance', 'repair',
            'insurance', 'tax', 'hoa', 'condo', 'townhouse', 'duplex', 'studio',
            'bedroom', 'bathroom', 'kitchen', 'living room', 'garage', 'balcony',
            'amenities', 'furnished', 'unfurnished', 'deposit', 'security deposit',
            'move-in', 'move-out', 'inspection', 'appraisal', 'closing', 'title',
            'deed', 'property management', 'real estate', 'broker', 'agent',
            'listing', 'showing', 'open house', 'offer', 'contract', 'agreement'
        ]
        
        self.financial_keywords = [
            'payment', 'bill', 'invoice', 'receipt', 'expense', 'cost', 'fee',
            'charge', 'refund', 'deposit', 'withdrawal', 'transaction', 'balance',
            'account', 'bank', 'credit', 'debit', 'loan', 'interest', 'rate',
            'budget', 'income', 'salary', 'wage', 'earnings', 'profit', 'loss'
        ]
    
    async def is_property_relevant(self, content: str, user_properties: List[Property]) -> Dict[str, Any]:
        """Determine if content is relevant to user's properties using LLM"""
        try:
            # First, do a quick keyword check for efficiency
            quick_relevance = self._quick_keyword_check(content)
            if not quick_relevance['is_relevant']:
                return {
                    'is_relevant': False,
                    'confidence': 0.0,
                    'reason': 'No property-related keywords found',
                    'method': 'keyword_check'
                }
            
            # Use LLM for more sophisticated analysis
            return await self._llm_relevance_check(content, user_properties)
            
        except Exception as e:
            print(f"Error in relevance filtering: {e}")
            # Fallback to keyword check
            return self._quick_keyword_check(content)
    
    def _quick_keyword_check(self, content: str) -> Dict[str, Any]:
        """Quick keyword-based relevance check"""
        content_lower = content.lower()
        
        # Check for property keywords
        property_matches = sum(1 for keyword in self.property_keywords if keyword in content_lower)
        financial_matches = sum(1 for keyword in self.financial_keywords if keyword in content_lower)
        
        # Calculate relevance score
        total_matches = property_matches + financial_matches
        confidence = min(total_matches / 10.0, 1.0)  # Normalize to 0-1
        
        is_relevant = total_matches >= 2  # At least 2 keyword matches
        
        return {
            'is_relevant': is_relevant,
            'confidence': confidence,
            'reason': f'Found {property_matches} property keywords and {financial_matches} financial keywords',
            'method': 'keyword_check'
        }
    
    async def _llm_relevance_check(self, content: str, user_properties: List[Property]) -> Dict[str, Any]:
        """Use LLM to determine relevance to user's properties"""
        try:
            # Prepare context about user's properties
            properties_context = self._format_properties_context(user_properties)
            
            # Create prompt for LLM
            prompt = f"""
You are analyzing content to determine if it's relevant to a user's properties and home management.

User's Properties:
{properties_context}

Content to analyze:
{content[:1000]}  # Limit content length

Please determine if this content is relevant to the user's property management, home ownership, rental activities, or property-related financial matters.

Consider relevance to:
- Property management and maintenance
- Rental/lease activities
- Property-related financial transactions
- Home improvement and repairs
- Property insurance and taxes
- Real estate transactions
- Property-related services and vendors

Respond with a JSON object containing:
- "is_relevant": boolean
- "confidence": number between 0.0 and 1.0
- "reason": brief explanation
- "property_connection": which property it relates to (if any)
"""

            # Get LLM response
            response = await llm_service.generate_response(
                user_query=prompt,
                context_data={},
                user_name="User"
            )
            
            # Parse LLM response
            try:
                # Extract JSON from response
                import json
                # Look for JSON in the response
                json_match = re.search(r'\{.*\}', response['response'], re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    return {
                        'is_relevant': result.get('is_relevant', False),
                        'confidence': float(result.get('confidence', 0.0)),
                        'reason': result.get('reason', 'LLM analysis'),
                        'property_connection': result.get('property_connection'),
                        'method': 'llm_analysis'
                    }
            except:
                pass
            
            # Fallback: analyze response text
            response_text = response['response'].lower()
            is_relevant = 'yes' in response_text or 'relevant' in response_text
            confidence = 0.7 if is_relevant else 0.3
            
            return {
                'is_relevant': is_relevant,
                'confidence': confidence,
                'reason': 'LLM analysis (parsed from text)',
                'method': 'llm_analysis'
            }
            
        except Exception as e:
            print(f"LLM relevance check error: {e}")
            # Fallback to keyword check
            return self._quick_keyword_check(content)
    
    def _format_properties_context(self, properties: List[Property]) -> str:
        """Format user properties for LLM context"""
        if not properties:
            return "No properties found"
        
        context = "User owns the following properties:\n"
        for prop in properties:
            context += f"- {prop.name}: {prop.address}\n"
        
        return context
    
    async def filter_emails_for_properties(self, user_id: int, emails: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter emails to only include property-relevant ones"""
        db = SessionLocal()
        try:
            # Get user's properties
            user_properties = db.query(Property).filter(Property.user_id == user_id).all()
            
            relevant_emails = []
            for email in emails:
                # Combine subject and body for analysis
                content = f"{email.get('subject', '')} {email.get('body', '')}"
                
                # Check relevance
                relevance = await self.is_property_relevant(content, user_properties)
                
                if relevance['is_relevant']:
                    email['relevance'] = relevance
                    relevant_emails.append(email)
            
            return relevant_emails
            
        except Exception as e:
            print(f"Error filtering emails: {e}")
            return emails  # Return all emails if filtering fails
        finally:
            db.close()
    
    async def filter_documents_for_properties(self, user_id: int, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter documents to only include property-relevant ones"""
        db = SessionLocal()
        try:
            # Get user's properties
            user_properties = db.query(Property).filter(Property.user_id == user_id).all()
            
            relevant_documents = []
            for doc in documents:
                # Use document title and content for analysis
                content = f"{doc.get('name', '')} {doc.get('content', '')}"
                
                # Check relevance
                relevance = await self.is_property_relevant(content, user_properties)
                
                if relevance['is_relevant']:
                    doc['relevance'] = relevance
                    relevant_documents.append(doc)
            
            return relevant_documents
            
        except Exception as e:
            print(f"Error filtering documents: {e}")
            return documents  # Return all documents if filtering fails
        finally:
            db.close()
    
    async def filter_calendar_events_for_properties(self, user_id: int, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter calendar events to only include property-relevant ones"""
        db = SessionLocal()
        try:
            # Get user's properties
            user_properties = db.query(Property).filter(Property.user_id == user_id).all()
            
            relevant_events = []
            for event in events:
                # Use event summary and description for analysis
                content = f"{event.get('summary', '')} {event.get('description', '')}"
                
                # Check relevance
                relevance = await self.is_property_relevant(content, user_properties)
                
                if relevance['is_relevant']:
                    event['relevance'] = relevance
                    relevant_events.append(event)
            
            return relevant_events
            
        except Exception as e:
            print(f"Error filtering calendar events: {e}")
            return events  # Return all events if filtering fails
        finally:
            db.close()

# Global instance
relevance_filter = RelevanceFilter()
