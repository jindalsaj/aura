from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from app.database import get_db
from app.models import User, Message, Document, Property, Expense
from app.services.llm_service import llm_service
import re
from datetime import datetime, timedelta
import asyncio

class ChatService:
    def __init__(self):
        pass
    
    def _get_db(self):
        return next(get_db())
    
    def _get_user_info(self, user_id: int) -> Dict[str, Any]:
        """Get user information for personalization"""
        db = self._get_db()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                return {
                    "name": user.name,
                    "email": user.email,
                    "picture": user.picture
                }
            return {}
        finally:
            db.close()
    
    def _extract_relevant_data(self, user_id: int, query: str) -> Dict[str, Any]:
        """Extract relevant data based on the query"""
        context_data = {}
        query_lower = query.lower()
        
        # Always include summary for context
        context_data["summary"] = self._get_summary(user_id)
        
        # Extract emails if relevant
        if any(word in query_lower for word in ['email', 'message', 'mail', 'inbox', 'sent', 'received']):
            context_data["emails"] = self._get_recent_emails(user_id, 20)
        
        # Extract documents if relevant
        if any(word in query_lower for word in ['document', 'file', 'pdf', 'attachment', 'drive', 'receipt', 'invoice']):
            context_data["documents"] = self._get_recent_documents(user_id, 20)
        
        # Extract properties if relevant
        if any(word in query_lower for word in ['property', 'properties', 'home', 'house', 'apartment', 'address']):
            context_data["properties"] = self._get_properties(user_id)
        
        # Extract expenses if relevant
        if any(word in query_lower for word in ['expense', 'expenses', 'cost', 'money', 'spent', 'bill', 'payment', 'budget']):
            context_data["expenses"] = self._get_recent_expenses(user_id, 20)
        
        # If no specific data type is mentioned, include a bit of everything for context
        if not any([
            any(word in query_lower for word in ['email', 'message', 'mail']),
            any(word in query_lower for word in ['document', 'file', 'pdf']),
            any(word in query_lower for word in ['property', 'home', 'house']),
            any(word in query_lower for word in ['expense', 'cost', 'money'])
        ]):
            # Include recent data from all sources for general queries
            context_data["emails"] = self._get_recent_emails(user_id, 5)
            context_data["documents"] = self._get_recent_documents(user_id, 5)
            context_data["properties"] = self._get_properties(user_id)
            context_data["expenses"] = self._get_recent_expenses(user_id, 5)
        
        return context_data
    
    def process_query(self, user_id: int, query: str) -> Dict[str, Any]:
        """
        Process a natural language query and return relevant data using LLM
        """
        try:
            # Get user info for personalization
            user_info = self._get_user_info(user_id)
            
            # Extract relevant data based on query
            context_data = self._extract_relevant_data(user_id, query)
            
            # Use LLM to generate intelligent response
            llm_result = asyncio.run(llm_service.generate_response(
                user_query=query,
                context_data=context_data,
                user_name=user_info.get('name')
            ))
            
            return {
                "response": llm_result["response"],
                "sources": llm_result["sources"],
                "confidence": llm_result["confidence"],
                "model_used": llm_result.get("model_used", "gpt-4o-mini")
            }
            
        except Exception as e:
            return {
                "response": f"I encountered an error processing your query: {str(e)}",
                "sources": [],
                "confidence": 0.0,
                "error": str(e)
            }
    
    def _analyze_intent(self, query: str) -> Dict[str, Any]:
        """
        Analyze the query to determine user intent
        """
        query_lower = query.lower()
        
        # Email-related intents
        if any(word in query_lower for word in ['email', 'message', 'sent', 'received']):
            if 'recent' in query_lower or 'latest' in query_lower:
                return {"type": "recent_emails", "limit": 10}
            elif 'from' in query_lower:
                # Extract sender from query
                sender_match = re.search(r'from\s+([a-zA-Z0-9@._-]+)', query_lower)
                if sender_match:
                    return {"type": "emails_from", "sender": sender_match.group(1)}
            elif 'about' in query_lower or 'regarding' in query_lower:
                # Extract topic from query
                topic_match = re.search(r'(?:about|regarding)\s+(.+)', query_lower)
                if topic_match:
                    return {"type": "emails_about", "topic": topic_match.group(1)}
            else:
                return {"type": "emails", "limit": 20}
        
        # Document-related intents
        elif any(word in query_lower for word in ['document', 'file', 'attachment', 'pdf', 'receipt']):
            if 'recent' in query_lower:
                return {"type": "recent_documents", "limit": 10}
            elif 'type' in query_lower or 'kind' in query_lower:
                doc_type_match = re.search(r'(?:type|kind)\s+(.+)', query_lower)
                if doc_type_match:
                    return {"type": "documents_by_type", "doc_type": doc_type_match.group(1)}
            else:
                return {"type": "documents", "limit": 20}
        
        # Property-related intents
        elif any(word in query_lower for word in ['property', 'properties', 'home', 'house', 'apartment']):
            return {"type": "properties"}
        
        # Expense-related intents
        elif any(word in query_lower for word in ['expense', 'expenses', 'cost', 'spent', 'money', 'bill']):
            if 'recent' in query_lower:
                return {"type": "recent_expenses", "limit": 10}
            elif 'category' in query_lower:
                category_match = re.search(r'category\s+(.+)', query_lower)
                if category_match:
                    return {"type": "expenses_by_category", "category": category_match.group(1)}
            else:
                return {"type": "expenses", "limit": 20}
        
        # Summary intents
        elif any(word in query_lower for word in ['summary', 'overview', 'total', 'count']):
            return {"type": "summary"}
        
        # Default to general search
        else:
            return {"type": "search", "query": query}
    
    def _extract_data(self, user_id: int, intent: Dict[str, Any], query: str) -> Dict[str, Any]:
        """
        Extract relevant data based on intent
        """
        results = {"sources": [], "confidence": 0.8}
        
        try:
            if intent["type"] == "recent_emails":
                emails = self._get_recent_emails(user_id, intent.get("limit", 10))
                results["emails"] = emails
                results["sources"].extend([{"type": "Gmail", "description": f"{len(emails)} recent emails"}])
                
            elif intent["type"] == "emails_from":
                emails = self._get_emails_from(user_id, intent["sender"])
                results["emails"] = emails
                results["sources"].extend([{"type": "Gmail", "description": f"emails from {intent['sender']}"}])
                
            elif intent["type"] == "emails_about":
                emails = self._get_emails_about(user_id, intent["topic"])
                results["emails"] = emails
                results["sources"].extend([{"type": "Gmail", "description": f"emails about {intent['topic']}"}])
                
            elif intent["type"] == "emails":
                emails = self._get_recent_emails(user_id, intent.get("limit", 20))
                results["emails"] = emails
                results["sources"].extend([{"type": "Gmail", "description": f"{len(emails)} emails"}])
                
            elif intent["type"] == "recent_documents":
                documents = self._get_recent_documents(user_id, intent.get("limit", 10))
                results["documents"] = documents
                results["sources"].extend([{"type": "Google Drive", "description": f"{len(documents)} recent documents"}])
                
            elif intent["type"] == "documents_by_type":
                documents = self._get_documents_by_type(user_id, intent["doc_type"])
                results["documents"] = documents
                results["sources"].extend([{"type": "Google Drive", "description": f"{intent['doc_type']} documents"}])
                
            elif intent["type"] == "documents":
                documents = self._get_recent_documents(user_id, intent.get("limit", 20))
                results["documents"] = documents
                results["sources"].extend([{"type": "Google Drive", "description": f"{len(documents)} documents"}])
                
            elif intent["type"] == "properties":
                properties = self._get_properties(user_id)
                results["properties"] = properties
                results["sources"].extend([{"type": "Properties", "description": f"{len(properties)} properties"}])
                
            elif intent["type"] == "recent_expenses":
                expenses = self._get_recent_expenses(user_id, intent.get("limit", 10))
                results["expenses"] = expenses
                results["sources"].extend([{"type": "Expenses", "description": f"{len(expenses)} recent expenses"}])
                
            elif intent["type"] == "expenses_by_category":
                expenses = self._get_expenses_by_category(user_id, intent["category"])
                results["expenses"] = expenses
                results["sources"].extend([{"type": "Expenses", "description": f"{intent['category']} category"}])
                
            elif intent["type"] == "expenses":
                expenses = self._get_recent_expenses(user_id, intent.get("limit", 20))
                results["expenses"] = expenses
                results["sources"].extend([{"type": "Expenses", "description": f"{len(expenses)} expenses"}])
                
            elif intent["type"] == "summary":
                summary = self._get_summary(user_id)
                results["summary"] = summary
                results["sources"].extend([{"type": "All Data Sources", "description": "Complete data overview"}])
                
            elif intent["type"] == "search":
                # General search across all data
                search_results = self._search_all_data(user_id, intent["query"])
                results.update(search_results)
                results["sources"].extend([{"type": "All Data Sources", "description": "Cross-source search"}])
                
        except Exception as e:
            results["error"] = str(e)
            results["confidence"] = 0.0
            
        return results
    
    def _get_recent_emails(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent emails for user"""
        db = self._get_db()
        try:
            emails = db.query(Message).filter(
                and_(
                    Message.user_id == user_id,
                    Message.source == 'gmail'
                )
            ).order_by(Message.message_date.desc()).limit(limit).all()
        finally:
            db.close()
        
        return [{
            "id": email.id,
            "sender": email.sender,
            "subject": email.meta_data.get("subject", "No Subject") if email.meta_data else "No Subject",
            "content": email.content[:200] + "..." if len(email.content) > 200 else email.content,
            "date": email.message_date.isoformat(),
            "source": "Gmail"
        } for email in emails]
    
    def _get_emails_from(self, user_id: int, sender: str) -> List[Dict[str, Any]]:
        """Get emails from specific sender"""
        db = self._get_db()
        try:
            emails = db.query(Message).filter(
                and_(
                    Message.user_id == user_id,
                    Message.source == 'gmail',
                    Message.sender.ilike(f"%{sender}%")
                )
            ).order_by(Message.message_date.desc()).limit(20).all()
        finally:
            db.close()
        
        return [{
            "id": email.id,
            "sender": email.sender,
            "subject": email.meta_data.get("subject", "No Subject") if email.meta_data else "No Subject",
            "content": email.content[:200] + "..." if len(email.content) > 200 else email.content,
            "date": email.message_date.isoformat(),
            "source": "Gmail"
        } for email in emails]
    
    def _get_emails_about(self, user_id: int, topic: str) -> List[Dict[str, Any]]:
        """Get emails about specific topic"""
        db = self._get_db()
        try:
            emails = db.query(Message).filter(
                and_(
                    Message.user_id == user_id,
                    Message.source == 'gmail',
                    or_(
                        Message.content.ilike(f"%{topic}%"),
                        Message.meta_data.contains({"subject": topic})
                    )
                )
            ).order_by(Message.message_date.desc()).limit(20).all()
        finally:
            db.close()
        
        return [{
            "id": email.id,
            "sender": email.sender,
            "subject": email.meta_data.get("subject", "No Subject") if email.meta_data else "No Subject",
            "content": email.content[:200] + "..." if len(email.content) > 200 else email.content,
            "date": email.message_date.isoformat(),
            "source": "Gmail"
        } for email in emails]
    
    def _get_recent_documents(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent documents for user"""
        db = self._get_db()
        try:
            documents = db.query(Document).filter(
                Document.user_id == user_id
            ).order_by(Document.created_at.desc()).limit(limit).all()
        finally:
            db.close()
        
        return [{
            "id": doc.id,
            "title": doc.title,
            "type": doc.document_type,
            "source": doc.source,
            "content": doc.content[:200] + "..." if doc.content and len(doc.content) > 200 else doc.content,
            "date": doc.created_at.isoformat()
        } for doc in documents]
    
    def _get_documents_by_type(self, user_id: int, doc_type: str) -> List[Dict[str, Any]]:
        """Get documents by type"""
        db = self._get_db()
        try:
            documents = db.query(Document).filter(
                and_(
                    Document.user_id == user_id,
                    Document.document_type.ilike(f"%{doc_type}%")
                )
            ).order_by(Document.created_at.desc()).limit(20).all()
        finally:
            db.close()
        
        return [{
            "id": doc.id,
            "title": doc.title,
            "type": doc.document_type,
            "source": doc.source,
            "content": doc.content[:200] + "..." if doc.content and len(doc.content) > 200 else doc.content,
            "date": doc.created_at.isoformat()
        } for doc in documents]
    
    def _get_properties(self, user_id: int) -> List[Dict[str, Any]]:
        """Get user properties"""
        db = self._get_db()
        try:
            properties = db.query(Property).filter(
                Property.user_id == user_id
            ).all()
        finally:
            db.close()
        
        return [{
            "id": prop.id,
            "name": prop.name,
            "address": prop.address,
            "type": prop.property_type,
            "created": prop.created_at.isoformat()
        } for prop in properties]
    
    def _get_recent_expenses(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent expenses for user"""
        db = self._get_db()
        try:
            expenses = db.query(Expense).filter(
                Expense.user_id == user_id
            ).order_by(Expense.transaction_date.desc()).limit(limit).all()
        finally:
            db.close()
        
        return [{
            "id": exp.id,
            "amount": exp.amount,
            "description": exp.description,
            "category": exp.category,
            "date": exp.transaction_date.isoformat(),
            "source": exp.source
        } for exp in expenses]
    
    def _get_expenses_by_category(self, user_id: int, category: str) -> List[Dict[str, Any]]:
        """Get expenses by category"""
        db = self._get_db()
        try:
            expenses = db.query(Expense).filter(
                and_(
                    Expense.user_id == user_id,
                    Expense.category.ilike(f"%{category}%")
                )
            ).order_by(Expense.transaction_date.desc()).limit(20).all()
        finally:
            db.close()
        
        return [{
            "id": exp.id,
            "amount": exp.amount,
            "description": exp.description,
            "category": exp.category,
            "date": exp.transaction_date.isoformat(),
            "source": exp.source
        } for exp in expenses]
    
    def _get_summary(self, user_id: int) -> Dict[str, Any]:
        """Get summary of all user data"""
        db = self._get_db()
        try:
            email_count = db.query(Message).filter(
                and_(Message.user_id == user_id, Message.source == 'gmail')
            ).count()
            
            document_count = db.query(Document).filter(
                Document.user_id == user_id
            ).count()
            
            property_count = db.query(Property).filter(
                Property.user_id == user_id
            ).count()
            
            expense_count = db.query(Expense).filter(
                Expense.user_id == user_id
            ).count()
            
            total_expenses = db.query(func.sum(Expense.amount)).filter(
                Expense.user_id == user_id
            ).scalar() or 0
        finally:
            db.close()
        
        return {
            "emails": email_count,
            "documents": document_count,
            "properties": property_count,
            "expenses": expense_count,
            "total_expense_amount": total_expenses
        }
    
    def _search_all_data(self, user_id: int, query: str) -> Dict[str, Any]:
        """Search across all data types"""
        results = {}
        
        # Search emails
        db = self._get_db()
        try:
            emails = db.query(Message).filter(
                and_(
                    Message.user_id == user_id,
                    Message.source == 'gmail',
                    Message.content.ilike(f"%{query}%")
                )
            ).limit(10).all()
        finally:
            db.close()
        
        results["emails"] = [{
            "id": email.id,
            "sender": email.sender,
            "subject": email.meta_data.get("subject", "No Subject") if email.meta_data else "No Subject",
            "content": email.content[:200] + "..." if len(email.content) > 200 else email.content,
            "date": email.message_date.isoformat(),
            "source": "Gmail"
        } for email in emails]
        
        # Search documents
        db = self._get_db()
        try:
            documents = db.query(Document).filter(
                and_(
                    Document.user_id == user_id,
                    or_(
                        Document.title.ilike(f"%{query}%"),
                        Document.content.ilike(f"%{query}%")
                    )
                )
            ).limit(10).all()
        finally:
            db.close()
        
        results["documents"] = [{
            "id": doc.id,
            "title": doc.title,
            "type": doc.document_type,
            "source": doc.source,
            "content": doc.content[:200] + "..." if doc.content and len(doc.content) > 200 else doc.content,
            "date": doc.created_at.isoformat()
        } for doc in documents]
        
        return results
    
    def _generate_response(self, intent: Dict[str, Any], results: Dict[str, Any], query: str) -> str:
        """
        Generate a natural language response based on intent and results
        """
        if "error" in results:
            return f"I encountered an error: {results['error']}"
        
        if intent["type"] == "recent_emails":
            emails = results.get("emails", [])
            if emails:
                response = f"I found {len(emails)} recent emails:\n\n"
                for email in emails[:5]:  # Show first 5
                    response += f"• From: {email['sender']}\n"
                    response += f"  Subject: {email['subject']}\n"
                    response += f"  Date: {email['date'][:10]}\n\n"
                if len(emails) > 5:
                    response += f"... and {len(emails) - 5} more emails."
                return response
            else:
                return "I don't see any recent emails in your Gmail data."
        
        elif intent["type"] == "emails_from":
            emails = results.get("emails", [])
            if emails:
                response = f"I found {len(emails)} emails from {intent['sender']}:\n\n"
                for email in emails[:5]:
                    response += f"• Subject: {email['subject']}\n"
                    response += f"  Date: {email['date'][:10]}\n\n"
                return response
            else:
                return f"I don't see any emails from {intent['sender']}."
        
        elif intent["type"] == "emails_about":
            emails = results.get("emails", [])
            if emails:
                response = f"I found {len(emails)} emails about {intent['topic']}:\n\n"
                for email in emails[:5]:
                    response += f"• From: {email['sender']}\n"
                    response += f"  Subject: {email['subject']}\n"
                    response += f"  Date: {email['date'][:10]}\n\n"
                return response
            else:
                return f"I don't see any emails about {intent['topic']}."
        
        elif intent["type"] == "recent_documents":
            documents = results.get("documents", [])
            if documents:
                response = f"I found {len(documents)} recent documents:\n\n"
                for doc in documents[:5]:
                    response += f"• {doc['title']} ({doc['type']})\n"
                    response += f"  Source: {doc['source']}\n"
                    response += f"  Date: {doc['date'][:10]}\n\n"
                return response
            else:
                return "I don't see any recent documents in your Google Drive."
        
        elif intent["type"] == "properties":
            properties = results.get("properties", [])
            if properties:
                response = f"You have {len(properties)} properties:\n\n"
                for prop in properties:
                    response += f"• {prop['name']}\n"
                    response += f"  Address: {prop['address']}\n"
                    response += f"  Type: {prop['type']}\n\n"
                return response
            else:
                return "I don't see any properties in your account. You can add properties in the Properties section."
        
        elif intent["type"] == "recent_expenses":
            expenses = results.get("expenses", [])
            if expenses:
                total = sum(exp['amount'] for exp in expenses)
                response = f"I found {len(expenses)} recent expenses totaling ${total:.2f}:\n\n"
                for exp in expenses[:5]:
                    response += f"• ${exp['amount']:.2f} - {exp['description']}\n"
                    response += f"  Category: {exp['category']}\n"
                    response += f"  Date: {exp['date'][:10]}\n\n"
                return response
            else:
                return "I don't see any recent expenses. You can add expenses manually or connect your bank account."
        
        elif intent["type"] == "summary":
            summary = results.get("summary", {})
            response = f"Here's a summary of your data:\n\n"
            response += f"• Emails: {summary.get('emails', 0)}\n"
            response += f"• Documents: {summary.get('documents', 0)}\n"
            response += f"• Properties: {summary.get('properties', 0)}\n"
            response += f"• Expenses: {summary.get('expenses', 0)} (Total: ${summary.get('total_expense_amount', 0):.2f})\n\n"
            response += "You can ask me specific questions about any of these data sources!"
            return response
        
        elif intent["type"] == "search":
            emails = results.get("emails", [])
            documents = results.get("documents", [])
            
            if emails or documents:
                response = f"I found results for '{query}':\n\n"
                if emails:
                    response += f"Emails ({len(emails)}):\n"
                    for email in emails[:3]:
                        response += f"• {email['subject']} from {email['sender']}\n"
                    response += "\n"
                
                if documents:
                    response += f"Documents ({len(documents)}):\n"
                    for doc in documents[:3]:
                        response += f"• {doc['title']} ({doc['type']})\n"
                    response += "\n"
                
                return response
            else:
                return f"I didn't find any results for '{query}' in your data."
        
        else:
            return "I understand your question, but I need more specific information to help you. Try asking about your emails, documents, properties, or expenses."

# Global instance
chat_service = ChatService()