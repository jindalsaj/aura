import os
import json
import requests
from typing import List, Dict, Any, Optional
from app.core.config import settings

class LLMService:
    def __init__(self):
        self.openai_available = bool(settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "your-openai-api-key")
        self.gemini_available = bool(settings.GOOGLE_GEMINI_API_KEY and settings.GOOGLE_GEMINI_API_KEY != "")
        self.model = "gpt-4o-mini"
        self.gemini_model = "gemini-1.5-flash"  # Fast and free model
        
        # Free alternatives
        self.huggingface_available = False  # Can be enabled with HF API key
        self.local_llm_available = False    # Can be enabled with local model
    
    async def generate_response(
        self, 
        user_query: str, 
        context_data: Dict[str, Any],
        user_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate an intelligent response using available LLM services
        Falls back to intelligent template responses if no LLM is available
        """
        try:
            # Try Google Gemini first (free tier)
            if self.gemini_available:
                try:
                    return await self._generate_gemini_response(user_query, context_data, user_name)
                except Exception as e:
                    print(f"Gemini error: {e}")
                    # Fall back to other options
            
            # Try OpenAI if available
            if self.openai_available:
                try:
                    return await self._generate_openai_response(user_query, context_data, user_name)
                except Exception as e:
                    print(f"OpenAI error: {e}")
                    # Fall back to intelligent responses
            
            # Try free alternatives
            if self.huggingface_available:
                try:
                    return await self._generate_huggingface_response(user_query, context_data, user_name)
                except Exception as e:
                    print(f"HuggingFace error: {e}")
            
            # Fall back to intelligent template responses
            return self._generate_intelligent_fallback(user_query, context_data, user_name)
            
        except Exception as e:
            return {
                "response": f"I apologize, but I'm having trouble processing your request right now. Error: {str(e)}",
                "sources": [],
                "confidence": 0.0,
                "error": str(e),
                "fallback": True
            }
    
    async def _generate_gemini_response(self, user_query: str, context_data: Dict[str, Any], user_name: Optional[str] = None) -> Dict[str, Any]:
        """Generate response using Google Gemini (free tier)"""
        import google.generativeai as genai
        
        # Configure Gemini
        genai.configure(api_key=settings.GOOGLE_GEMINI_API_KEY)
        model = genai.GenerativeModel(self.gemini_model)
        
        # Prepare the context for the LLM
        context_prompt = self._prepare_context_prompt(context_data, user_name)
        
        # Create the system prompt
        system_prompt = f"""You are Aura, a Personal Home & Property Assistant AI. You help users manage their personal data including emails, documents, properties, and expenses.

Your role:
- Analyze the user's data and provide intelligent insights
- Answer questions about their emails, documents, properties, and expenses
- Provide helpful summaries and recommendations
- Be conversational, helpful, and professional
- Always cite your sources when referencing specific data

User's data context:
{context_prompt}

Guidelines:
- If the user asks about data that doesn't exist, explain what data is available
- Provide specific examples from their data when relevant
- Suggest actions they can take based on their data
- Be concise but informative
- Use a friendly, professional tone
- Format your response with clear sections and bullet points when helpful"""

        # Create the full prompt
        full_prompt = f"{system_prompt}\n\nUser query: {user_query}"

        # Generate response
        response = model.generate_content(full_prompt)
        
        # Extract the response
        llm_response = response.text
        
        # Determine confidence based on data availability
        confidence = self._calculate_confidence(context_data, user_query)
        
        # Extract sources from context
        sources = self._extract_sources(context_data)
        
        return {
            "response": llm_response,
            "sources": sources,
            "confidence": confidence,
            "model_used": self.gemini_model
        }
    
    async def _generate_openai_response(self, user_query: str, context_data: Dict[str, Any], user_name: Optional[str] = None) -> Dict[str, Any]:
        """Generate response using OpenAI (if available and within quota)"""
        from openai import OpenAI
        
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Prepare the context for the LLM
        context_prompt = self._prepare_context_prompt(context_data, user_name)
        
        # Create the system prompt
        system_prompt = f"""You are Aura, a Personal Home & Property Assistant AI. You help users manage their personal data including emails, documents, properties, and expenses.

Your role:
- Analyze the user's data and provide intelligent insights
- Answer questions about their emails, documents, properties, and expenses
- Provide helpful summaries and recommendations
- Be conversational, helpful, and professional
- Always cite your sources when referencing specific data

User's data context:
{context_prompt}

Guidelines:
- If the user asks about data that doesn't exist, explain what data is available
- Provide specific examples from their data when relevant
- Suggest actions they can take based on their data
- Be concise but informative
- Use a friendly, professional tone"""

        # Create the user message
        user_message = f"User query: {user_query}"

        # Make the API call with privacy protection
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=1000,
            temperature=0.7,
            user="aura-user"
        )

        # Extract the response
        llm_response = response.choices[0].message.content
        
        # Determine confidence based on data availability
        confidence = self._calculate_confidence(context_data, user_query)
        
        # Extract sources from context
        sources = self._extract_sources(context_data)
        
        return {
            "response": llm_response,
            "sources": sources,
            "confidence": confidence,
            "model_used": self.model
        }
    
    async def _generate_huggingface_response(self, user_query: str, context_data: Dict[str, Any], user_name: Optional[str] = None) -> Dict[str, Any]:
        """Generate response using HuggingFace free models"""
        # This would use HuggingFace's free inference API
        # For now, fall back to intelligent responses
        return self._generate_intelligent_fallback(user_query, context_data, user_name)
    
    def _generate_intelligent_fallback(self, user_query: str, context_data: Dict[str, Any], user_name: Optional[str] = None) -> Dict[str, Any]:
        """Generate intelligent responses without external LLM"""
        query_lower = user_query.lower()
        
        # Analyze the query to provide intelligent responses
        if any(word in query_lower for word in ['calendar', 'invite', 'meeting', 'appointment']):
            return self._handle_calendar_query(context_data, user_query)
        elif any(word in query_lower for word in ['email', 'message', 'mail', 'inbox']):
            return self._handle_email_query(context_data, user_query)
        elif any(word in query_lower for word in ['document', 'file', 'pdf', 'attachment']):
            return self._handle_document_query(context_data, user_query)
        elif any(word in query_lower for word in ['property', 'home', 'house', 'apartment']):
            return self._handle_property_query(context_data, user_query)
        elif any(word in query_lower for word in ['expense', 'cost', 'money', 'spent', 'bill']):
            return self._handle_expense_query(context_data, user_query)
        elif any(word in query_lower for word in ['summary', 'overview', 'total', 'count']):
            return self._handle_summary_query(context_data, user_query)
        else:
            return self._handle_general_query(context_data, user_query)
    
    def _handle_calendar_query(self, context_data: Dict[str, Any], user_query: str) -> Dict[str, Any]:
        """Handle calendar-related queries intelligently"""
        emails = context_data.get("emails", [])
        
        # Look for calendar-related emails
        calendar_emails = []
        for email in emails:
            subject = email.get('subject', '').lower()
            content = email.get('content', '').lower()
            if any(word in subject or word in content for word in ['calendar', 'invite', 'meeting', 'appointment', 'event']):
                calendar_emails.append(email)
        
        if calendar_emails:
            response = f"I found {len(calendar_emails)} calendar-related emails in your inbox:\n\n"
            for email in calendar_emails[:3]:
                response += f"• {email.get('subject', 'No Subject')}\n"
                response += f"  From: {email.get('sender', 'Unknown')}\n"
                response += f"  Date: {email.get('date', 'Unknown')[:10]}\n\n"
            
            if len(calendar_emails) > 3:
                response += f"... and {len(calendar_emails) - 3} more calendar-related emails."
        else:
            response = "I don't see any calendar invites in your recent emails. Calendar invites typically come as email invitations. You might want to check your email for meeting invitations or calendar notifications."
        
        return {
            "response": response,
            "sources": [{"type": "Gmail", "description": f"{len(emails)} emails analyzed"}],
            "confidence": 0.8,
            "fallback": True
        }
    
    def _handle_email_query(self, context_data: Dict[str, Any], user_query: str) -> Dict[str, Any]:
        """Handle email-related queries intelligently"""
        emails = context_data.get("emails", [])
        
        if emails:
            # Analyze email patterns
            recent_emails = emails[:5]
            senders = {}
            subjects = []
            
            for email in recent_emails:
                sender = email.get('sender', 'Unknown')
                senders[sender] = senders.get(sender, 0) + 1
                subjects.append(email.get('subject', 'No Subject'))
            
            # Find most frequent sender
            top_sender = max(senders.items(), key=lambda x: x[1]) if senders else None
            
            response = f"I found {len(emails)} emails in your Gmail. Here's what I can tell you:\n\n"
            response += f"**Recent Activity:**\n"
            for email in recent_emails:
                response += f"• {email.get('subject', 'No Subject')}\n"
                response += f"  From: {email.get('sender', 'Unknown')}\n"
                response += f"  Date: {email.get('date', 'Unknown')[:10]}\n\n"
            
            if top_sender:
                response += f"**Most Frequent Sender:** {top_sender[0]} ({top_sender[1]} emails)\n\n"
            
            response += "You can ask me to find emails from specific senders or about specific topics!"
        else:
            response = "I don't see any emails in your Gmail data. Make sure you've connected your Gmail account and synced your emails."
        
        return {
            "response": response,
            "sources": [{"type": "Gmail", "description": f"{len(emails)} emails analyzed"}],
            "confidence": 0.8,
            "fallback": True
        }
    
    def _handle_document_query(self, context_data: Dict[str, Any], user_query: str) -> Dict[str, Any]:
        """Handle document-related queries intelligently"""
        documents = context_data.get("documents", [])
        
        if documents:
            response = f"I found {len(documents)} documents in your Google Drive:\n\n"
            
            # Group by type
            doc_types = {}
            for doc in documents:
                doc_type = doc.get('type', 'Unknown')
                doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
            
            response += "**Document Types:**\n"
            for doc_type, count in doc_types.items():
                response += f"• {doc_type}: {count} documents\n"
            
            response += "\n**Recent Documents:**\n"
            for doc in documents[:5]:
                response += f"• {doc.get('title', 'Unknown')}\n"
                response += f"  Type: {doc.get('type', 'Unknown')}\n"
                response += f"  Date: {doc.get('date', 'Unknown')[:10]}\n\n"
        else:
            response = "I don't see any documents in your Google Drive. Make sure you've connected your Google Drive and synced your files."
        
        return {
            "response": response,
            "sources": [{"type": "Google Drive", "description": f"{len(documents)} documents analyzed"}],
            "confidence": 0.8,
            "fallback": True
        }
    
    def _handle_property_query(self, context_data: Dict[str, Any], user_query: str) -> Dict[str, Any]:
        """Handle property-related queries intelligently"""
        properties = context_data.get("properties", [])
        
        if properties:
            response = f"You have {len(properties)} properties:\n\n"
            for prop in properties:
                response += f"**{prop.get('name', 'Unknown Property')}**\n"
                response += f"• Address: {prop.get('address', 'Unknown')}\n"
                response += f"• Type: {prop.get('type', 'Unknown')}\n"
                response += f"• Added: {prop.get('created', 'Unknown')[:10]}\n\n"
            
            response += "You can ask me about expenses related to these properties or add more properties in the Properties section."
        else:
            response = "I don't see any properties in your account. You can add properties in the Properties section to track your homes, apartments, or other real estate."
        
        return {
            "response": response,
            "sources": [{"type": "Properties", "description": f"{len(properties)} properties analyzed"}],
            "confidence": 0.8,
            "fallback": True
        }
    
    def _handle_expense_query(self, context_data: Dict[str, Any], user_query: str) -> Dict[str, Any]:
        """Handle expense-related queries intelligently"""
        expenses = context_data.get("expenses", [])
        
        if expenses:
            total_amount = sum(exp.get('amount', 0) for exp in expenses)
            
            # Group by category
            categories = {}
            for exp in expenses:
                category = exp.get('category', 'Uncategorized')
                categories[category] = categories.get(category, 0) + 1
            
            response = f"I found {len(expenses)} expenses totaling ${total_amount:.2f}:\n\n"
            
            response += "**Expense Categories:**\n"
            for category, count in categories.items():
                response += f"• {category}: {count} expenses\n"
            
            response += "\n**Recent Expenses:**\n"
            for exp in expenses[:5]:
                response += f"• ${exp.get('amount', 0):.2f} - {exp.get('description', 'No description')}\n"
                response += f"  Category: {exp.get('category', 'Unknown')}\n"
                response += f"  Date: {exp.get('date', 'Unknown')[:10]}\n\n"
        else:
            response = "I don't see any expenses in your account. You can add expenses manually or connect your bank account to automatically track transactions."
        
        return {
            "response": response,
            "sources": [{"type": "Expenses", "description": f"{len(expenses)} expenses analyzed"}],
            "confidence": 0.8,
            "fallback": True
        }
    
    def _handle_summary_query(self, context_data: Dict[str, Any], user_query: str) -> Dict[str, Any]:
        """Handle summary queries intelligently"""
        summary = context_data.get("summary", {})
        
        response = "Here's a comprehensive summary of your data:\n\n"
        response += f"📧 **Emails:** {summary.get('emails', 0)} messages in Gmail\n"
        response += f"📄 **Documents:** {summary.get('documents', 0)} files in Google Drive\n"
        response += f"🏠 **Properties:** {summary.get('properties', 0)} properties tracked\n"
        response += f"💰 **Expenses:** {summary.get('expenses', 0)} transactions (Total: ${summary.get('total_expense_amount', 0):.2f})\n\n"
        
        # Add insights
        if summary.get('emails', 0) > 0:
            response += "💡 **Insights:**\n"
            response += "• You have a good amount of email data for analysis\n"
            if summary.get('documents', 0) > 0:
                response += "• Your documents are synced and ready for review\n"
            if summary.get('properties', 0) > 0:
                response += "• Your properties are set up for expense tracking\n"
            if summary.get('expenses', 0) > 0:
                response += "• Your expense data is available for budgeting insights\n"
        
        response += "\nYou can ask me specific questions about any of these data sources!"
        
        return {
            "response": response,
            "sources": [{"type": "All Data Sources", "description": "Complete data overview analyzed"}],
            "confidence": 0.9,
            "fallback": True
        }
    
    def _handle_general_query(self, context_data: Dict[str, Any], user_query: str) -> Dict[str, Any]:
        """Handle general queries intelligently"""
        summary = context_data.get("summary", {})
        
        response = f"I understand you're asking: '{user_query}'\n\n"
        response += "Based on your available data, I can help you with:\n\n"
        
        if summary.get('emails', 0) > 0:
            response += "📧 **Email Analysis:** Find specific emails, analyze patterns, or get summaries\n"
        if summary.get('documents', 0) > 0:
            response += "📄 **Document Search:** Find files, analyze content, or organize by type\n"
        if summary.get('properties', 0) > 0:
            response += "🏠 **Property Management:** Track expenses, get property insights\n"
        if summary.get('expenses', 0) > 0:
            response += "💰 **Expense Analysis:** Budget insights, category breakdowns, spending patterns\n"
        
        response += "\nTry asking more specific questions like:\n"
        response += "• 'Show me my recent emails'\n"
        response += "• 'What documents do I have?'\n"
        response += "• 'Tell me about my properties'\n"
        response += "• 'Give me a summary of my expenses'"
        
        return {
            "response": response,
            "sources": [{"type": "All Data Sources", "description": "General data overview"}],
            "confidence": 0.7,
            "fallback": True
        }
    
    def _prepare_context_prompt(self, context_data: Dict[str, Any], user_name: Optional[str] = None) -> str:
        """Prepare the context data for the LLM prompt with privacy protection"""
        context_parts = []
        
        # Sanitize user name for privacy
        if user_name:
            sanitized_name = self._sanitize_personal_data(user_name)
            context_parts.append(f"User: {sanitized_name}")
        
        # Add email context
        if "emails" in context_data and context_data["emails"]:
            emails = context_data["emails"]
            context_parts.append(f"Recent Emails ({len(emails)}):")
            for email in emails[:5]:  # Show first 5 emails
                # Sanitize sender email
                sender = self._sanitize_personal_data(email.get('sender', 'Unknown'))
                context_parts.append(f"- From: {sender}")
                context_parts.append(f"  Subject: {email.get('subject', 'No Subject')}")
                context_parts.append(f"  Date: {email.get('date', 'Unknown')}")
                if email.get('content'):
                    # Sanitize email content
                    sanitized_content = self._sanitize_email_content(email['content'])
                    context_parts.append(f"  Preview: {sanitized_content}")
                context_parts.append("")
        
        # Add document context
        if "documents" in context_data and context_data["documents"]:
            documents = context_data["documents"]
            context_parts.append(f"Documents ({len(documents)}):")
            for doc in documents[:5]:  # Show first 5 documents
                context_parts.append(f"- Title: {doc.get('title', 'Unknown')}")
                context_parts.append(f"  Type: {doc.get('type', 'Unknown')}")
                context_parts.append(f"  Source: {doc.get('source', 'Unknown')}")
                context_parts.append(f"  Date: {doc.get('date', 'Unknown')}")
                if doc.get('content'):
                    # Sanitize document content
                    sanitized_content = self._sanitize_document_content(doc['content'])
                    context_parts.append(f"  Preview: {sanitized_content}")
                context_parts.append("")
        
        # Add property context
        if "properties" in context_data and context_data["properties"]:
            properties = context_data["properties"]
            context_parts.append(f"Properties ({len(properties)}):")
            for prop in properties:
                context_parts.append(f"- Name: {prop.get('name', 'Unknown')}")
                context_parts.append(f"  Address: {prop.get('address', 'Unknown')}")
                context_parts.append(f"  Type: {prop.get('type', 'Unknown')}")
                context_parts.append("")
        
        # Add expense context
        if "expenses" in context_data and context_data["expenses"]:
            expenses = context_data["expenses"]
            total_amount = sum(exp.get('amount', 0) for exp in expenses)
            context_parts.append(f"Recent Expenses ({len(expenses)}, Total: ${total_amount:.2f}):")
            for exp in expenses[:5]:  # Show first 5 expenses
                context_parts.append(f"- Amount: ${exp.get('amount', 0):.2f}")
                context_parts.append(f"  Description: {exp.get('description', 'Unknown')}")
                context_parts.append(f"  Category: {exp.get('category', 'Unknown')}")
                context_parts.append(f"  Date: {exp.get('date', 'Unknown')}")
                context_parts.append("")
        
        # Add summary context
        if "summary" in context_data:
            summary = context_data["summary"]
            context_parts.append("Data Summary:")
            context_parts.append(f"- Total Emails: {summary.get('emails', 0)}")
            context_parts.append(f"- Total Documents: {summary.get('documents', 0)}")
            context_parts.append(f"- Total Properties: {summary.get('properties', 0)}")
            context_parts.append(f"- Total Expenses: {summary.get('expenses', 0)}")
            context_parts.append(f"- Total Expense Amount: ${summary.get('total_expense_amount', 0):.2f}")
            context_parts.append("")
        
        return "\n".join(context_parts) if context_parts else "No data available"
    
    def _calculate_confidence(self, context_data: Dict[str, Any], user_query: str) -> float:
        """Calculate confidence based on data availability and query relevance"""
        base_confidence = 0.5
        
        # Increase confidence if we have relevant data
        query_lower = user_query.lower()
        
        if any(word in query_lower for word in ['email', 'message']) and context_data.get('emails'):
            base_confidence += 0.2
        if any(word in query_lower for word in ['document', 'file']) and context_data.get('documents'):
            base_confidence += 0.2
        if any(word in query_lower for word in ['property', 'home', 'house']) and context_data.get('properties'):
            base_confidence += 0.2
        if any(word in query_lower for word in ['expense', 'cost', 'money']) and context_data.get('expenses'):
            base_confidence += 0.2
        if any(word in query_lower for word in ['summary', 'overview']) and context_data.get('summary'):
            base_confidence += 0.1
        
        return min(base_confidence, 0.95)  # Cap at 95%
    
    def _extract_sources(self, context_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract source information from context data"""
        sources = []
        
        if context_data.get('emails'):
            sources.append({
                "type": "Gmail",
                "description": f"{len(context_data['emails'])} emails analyzed"
            })
        
        if context_data.get('documents'):
            sources.append({
                "type": "Google Drive", 
                "description": f"{len(context_data['documents'])} documents analyzed"
            })
        
        if context_data.get('properties'):
            sources.append({
                "type": "Properties",
                "description": f"{len(context_data['properties'])} properties analyzed"
            })
        
        if context_data.get('expenses'):
            sources.append({
                "type": "Expenses",
                "description": f"{len(context_data['expenses'])} expenses analyzed"
            })
        
        if context_data.get('summary'):
            sources.append({
                "type": "Data Summary",
                "description": "Complete data overview analyzed"
            })
        
        return sources
    
    def _sanitize_personal_data(self, text: str) -> str:
        """Sanitize personal data for privacy protection"""
        if not text:
            return text
        
        # Remove or mask email addresses
        import re
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
        
        # Remove or mask phone numbers
        text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', text)
        
        # Remove or mask SSN patterns
        text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', text)
        
        # Remove or mask credit card patterns
        text = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CARD]', text)
        
        return text
    
    def _sanitize_email_content(self, content: str) -> str:
        """Sanitize email content to remove sensitive information"""
        if not content:
            return content
        
        # Limit content length to reduce data exposure
        max_length = 500
        if len(content) > max_length:
            content = content[:max_length] + "..."
        
        # Sanitize personal data
        content = self._sanitize_personal_data(content)
        
        return content
    
    def _sanitize_document_content(self, content: str) -> str:
        """Sanitize document content to remove sensitive information"""
        if not content:
            return content
        
        # Limit content length to reduce data exposure
        max_length = 300
        if len(content) > max_length:
            content = content[:max_length] + "..."
        
        # Sanitize personal data
        content = self._sanitize_personal_data(content)
        
        return content

# Global instance
llm_service = LLMService()