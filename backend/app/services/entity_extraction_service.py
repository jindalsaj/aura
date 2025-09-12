import re
import spacy
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

from app.database import get_db
from app.models import User, Message, Document, Expense, ServiceProvider, Property
from sqlalchemy.orm import Session


class EntityExtractionService:
    def __init__(self):
        # Load spaCy model (you'll need to download it: python -m spacy download en_core_web_sm)
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            print("spaCy model not found. Please install: python -m spacy download en_core_web_sm")
            self.nlp = None
    
    def extract_entities_from_text(self, text: str) -> Dict[str, List[str]]:
        """Extract entities from text using spaCy"""
        if not self.nlp or not text:
            return {}
        
        doc = self.nlp(text)
        entities = defaultdict(list)
        
        for ent in doc.ents:
            entities[ent.label_].append(ent.text)
        
        return dict(entities)
    
    def extract_property_addresses(self, text: str) -> List[Dict[str, Any]]:
        """Extract property addresses from text"""
        addresses = []
        
        # Common address patterns
        address_patterns = [
            r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Way|Place|Pl|Court|Ct)',
            r'\d+\s+[A-Za-z\s]+(?:Apartment|Apt|Unit|Suite|Ste)\s*\d*',
            r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Way|Place|Pl|Court|Ct)\s*,\s*[A-Za-z\s]+,\s*[A-Z]{2}\s*\d{5}'
        ]
        
        for pattern in address_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                addresses.append({
                    'address': match.group().strip(),
                    'confidence': 0.7,
                    'start': match.start(),
                    'end': match.end()
                })
        
        return addresses
    
    def extract_phone_numbers(self, text: str) -> List[str]:
        """Extract phone numbers from text"""
        phone_patterns = [
            r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # US phone numbers
            r'\+\d{1,3}[-.\s]?\d{3,4}[-.\s]?\d{3,4}[-.\s]?\d{3,4}',  # International
            r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}'  # Simple format
        ]
        
        phone_numbers = []
        for pattern in phone_patterns:
            matches = re.findall(pattern, text)
            phone_numbers.extend(matches)
        
        return list(set(phone_numbers))  # Remove duplicates
    
    def extract_email_addresses(self, text: str) -> List[str]:
        """Extract email addresses from text"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        return list(set(emails))
    
    def extract_monetary_amounts(self, text: str) -> List[Dict[str, Any]]:
        """Extract monetary amounts from text"""
        amount_patterns = [
            r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # $1,234.56
            r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*dollars?',  # 1234.56 dollars
            r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*USD',  # 1234.56 USD
        ]
        
        amounts = []
        for pattern in amount_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                amount_str = match.group(1).replace(',', '')
                try:
                    amount = float(amount_str)
                    amounts.append({
                        'amount': amount,
                        'text': match.group(),
                        'confidence': 0.8
                    })
                except ValueError:
                    continue
        
        return amounts
    
    def extract_dates(self, text: str) -> List[Dict[str, Any]]:
        """Extract dates from text"""
        date_patterns = [
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # MM/DD/YYYY or MM-DD-YYYY
            r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',  # YYYY/MM/DD or YYYY-MM-DD
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',  # Month DD, YYYY
            r'\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b'  # DD Month YYYY
        ]
        
        dates = []
        for pattern in date_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                dates.append({
                    'date': match.group(),
                    'confidence': 0.7,
                    'start': match.start(),
                    'end': match.end()
                })
        
        return dates
    
    def extract_service_providers(self, text: str) -> List[Dict[str, Any]]:
        """Extract service provider information from text"""
        providers = []
        
        # Service provider keywords
        service_keywords = {
            'plumber': ['plumber', 'plumbing', 'pipe', 'leak', 'drain', 'toilet', 'faucet'],
            'electrician': ['electrician', 'electrical', 'wiring', 'outlet', 'circuit', 'breaker'],
            'contractor': ['contractor', 'construction', 'renovation', 'repair', 'remodel'],
            'cleaner': ['cleaner', 'cleaning', 'housekeeping', 'maid', 'janitor'],
            'landscaper': ['landscaper', 'landscaping', 'lawn', 'garden', 'yard', 'mowing'],
            'pest_control': ['pest', 'exterminator', 'bug', 'rodent', 'termite'],
            'hvac': ['hvac', 'heating', 'cooling', 'air conditioning', 'furnace', 'ac'],
            'appliance_repair': ['appliance', 'repair', 'washer', 'dryer', 'refrigerator', 'dishwasher'],
            'locksmith': ['locksmith', 'lock', 'key', 'deadbolt'],
            'painter': ['painter', 'painting', 'paint', 'brush', 'roller']
        }
        
        text_lower = text.lower()
        
        for service_type, keywords in service_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    # Find the context around the keyword
                    start = text_lower.find(keyword)
                    if start != -1:
                        context_start = max(0, start - 50)
                        context_end = min(len(text), start + len(keyword) + 50)
                        context = text[context_start:context_end]
                        
                        # Extract potential business name or contact info
                        business_name = self._extract_business_name(context, keyword)
                        phone_numbers = self.extract_phone_numbers(context)
                        emails = self.extract_email_addresses(context)
                        
                        providers.append({
                            'service_type': service_type,
                            'keyword': keyword,
                            'context': context,
                            'business_name': business_name,
                            'phone_numbers': phone_numbers,
                            'emails': emails,
                            'confidence': 0.6
                        })
        
        return providers
    
    def _extract_business_name(self, context: str, keyword: str) -> Optional[str]:
        """Extract potential business name from context"""
        # Look for capitalized words near the keyword
        words = context.split()
        keyword_index = -1
        
        for i, word in enumerate(words):
            if keyword.lower() in word.lower():
                keyword_index = i
                break
        
        if keyword_index == -1:
            return None
        
        # Look for capitalized words before and after the keyword
        business_words = []
        
        # Check words before keyword
        for i in range(max(0, keyword_index - 3), keyword_index):
            word = words[i]
            if word[0].isupper() and len(word) > 2:
                business_words.append(word)
        
        # Check words after keyword
        for i in range(keyword_index + 1, min(len(words), keyword_index + 4)):
            word = words[i]
            if word[0].isupper() and len(word) > 2:
                business_words.append(word)
        
        return ' '.join(business_words) if business_words else None
    
    def process_user_data(self, user_id: int) -> Dict[str, Any]:
        """Process all user data to extract entities and relationships"""
        db = next(get_db())
        try:
            # Get all user data
            messages = db.query(Message).filter(Message.user_id == user_id).all()
            documents = db.query(Document).filter(Document.user_id == user_id).all()
            expenses = db.query(Expense).filter(Expense.user_id == user_id).all()
            
            extracted_entities = {
                'properties': [],
                'service_providers': [],
                'addresses': [],
                'phone_numbers': [],
                'emails': [],
                'amounts': [],
                'dates': []
            }
            
            # Process messages
            for message in messages:
                entities = self._extract_entities_from_message(message)
                self._merge_entities(extracted_entities, entities)
            
            # Process documents
            for document in documents:
                if document.content:
                    entities = self._extract_entities_from_document(document)
                    self._merge_entities(extracted_entities, entities)
            
            # Process expenses
            for expense in expenses:
                entities = self._extract_entities_from_expense(expense)
                self._merge_entities(extracted_entities, entities)
            
            # Store extracted service providers
            self._store_service_providers(user_id, extracted_entities['service_providers'])
            
            return {
                'total_entities': sum(len(v) for v in extracted_entities.values()),
                'entities': extracted_entities
            }
            
        finally:
            db.close()
    
    def _extract_entities_from_message(self, message: Message) -> Dict[str, List[Any]]:
        """Extract entities from a message"""
        entities = {
            'addresses': [],
            'phone_numbers': [],
            'emails': [],
            'amounts': [],
            'dates': [],
            'service_providers': []
        }
        
        if message.content:
            entities['addresses'] = self.extract_property_addresses(message.content)
            entities['phone_numbers'] = self.extract_phone_numbers(message.content)
            entities['emails'] = self.extract_email_addresses(message.content)
            entities['amounts'] = self.extract_monetary_amounts(message.content)
            entities['dates'] = self.extract_dates(message.content)
            entities['service_providers'] = self.extract_service_providers(message.content)
        
        return entities
    
    def _extract_entities_from_document(self, document: Document) -> Dict[str, List[Any]]:
        """Extract entities from a document"""
        entities = {
            'addresses': [],
            'phone_numbers': [],
            'emails': [],
            'amounts': [],
            'dates': [],
            'service_providers': []
        }
        
        if document.content:
            entities['addresses'] = self.extract_property_addresses(document.content)
            entities['phone_numbers'] = self.extract_phone_numbers(document.content)
            entities['emails'] = self.extract_email_addresses(document.content)
            entities['amounts'] = self.extract_monetary_amounts(document.content)
            entities['dates'] = self.extract_dates(document.content)
            entities['service_providers'] = self.extract_service_providers(document.content)
        
        return entities
    
    def _extract_entities_from_expense(self, expense: Expense) -> Dict[str, List[Any]]:
        """Extract entities from an expense"""
        entities = {
            'addresses': [],
            'phone_numbers': [],
            'emails': [],
            'amounts': [],
            'dates': [],
            'service_providers': []
        }
        
        if expense.description:
            entities['service_providers'] = self.extract_service_providers(expense.description)
        
        # Add the expense amount
        entities['amounts'].append({
            'amount': expense.amount,
            'text': f"${expense.amount}",
            'confidence': 1.0
        })
        
        return entities
    
    def _merge_entities(self, target: Dict[str, List[Any]], source: Dict[str, List[Any]]):
        """Merge entities from source into target"""
        for key, values in source.items():
            if key in target:
                target[key].extend(values)
    
    def _store_service_providers(self, user_id: int, providers: List[Dict[str, Any]]):
        """Store extracted service providers in database"""
        db = next(get_db())
        try:
            for provider_data in providers:
                # Check if provider already exists
                existing = None
                if provider_data.get('phone_numbers'):
                    for phone in provider_data['phone_numbers']:
                        existing = db.query(ServiceProvider).filter(
                            ServiceProvider.contact_info['phone'].astext == phone
                        ).first()
                        if existing:
                            break
                
                if existing:
                    # Update existing provider
                    if provider_data.get('business_name'):
                        existing.name = provider_data['business_name']
                    existing.last_used = datetime.now()
                    continue
                
                # Create new service provider
                contact_info = {}
                if provider_data.get('phone_numbers'):
                    contact_info['phone'] = provider_data['phone_numbers'][0]
                if provider_data.get('emails'):
                    contact_info['email'] = provider_data['emails'][0]
                
                provider = ServiceProvider(
                    name=provider_data.get('business_name', f"Provider {provider_data['service_type']}"),
                    contact_info=contact_info,
                    provider_type=provider_data['service_type'],
                    last_used=datetime.now()
                )
                
                db.add(provider)
            
            db.commit()
            
        except Exception as e:
            db.rollback()
            print(f"Error storing service providers: {e}")
        finally:
            db.close()


# Global instance
entity_extraction_service = EntityExtractionService()
