"""
Lightweight Supabase Client for Memory-Constrained Environments
==============================================================

A minimal HTTP-based client for Supabase that avoids the memory overhead
of the full SDK, specifically designed for Vercel serverless functions.
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx
from src.models import ProcessedEmail


class LightweightSupabaseClient:
    """Lightweight HTTP-based Supabase client."""
    
    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        self.base_url = url or os.getenv("SUPABASE_URL")
        self.api_key = key or os.getenv("SUPABASE_ANON_KEY")
        
        if not self.base_url or not self.api_key:
            raise ValueError("Supabase URL and API key are required")
        
        # Ensure URL ends with /
        if not self.base_url.endswith('/'):
            self.base_url += '/'
        
        self.rest_url = urljoin(self.base_url, 'rest/v1/')
        
        # Default headers
        self.headers = {
            'apikey': self.api_key,
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }
    
    async def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make HTTP request to Supabase REST API."""
        url = urljoin(self.rest_url, endpoint)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method.upper() == 'GET':
                response = await client.get(url, headers=self.headers)
            elif method.upper() == 'POST':
                response = await client.post(url, headers=self.headers, json=data)
            elif method.upper() == 'PATCH':
                response = await client.patch(url, headers=self.headers, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json() if response.content else {}
    
    async def insert_email(self, email_data: Dict[str, Any]) -> str:
        """Insert email into Supabase."""
        try:
            result = await self._request('POST', 'emails', email_data)
            if result and len(result) > 0:
                return result[0]['id']
            raise ValueError("No email ID returned from insert")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:  # Conflict - email already exists
                # Try to get existing email ID
                existing = await self.get_email_by_message_id(email_data['message_id'])
                if existing:
                    return existing['id']
            raise ValueError(f"Failed to insert email: {e.response.text}")
    
    async def get_email_by_message_id(self, message_id: str) -> Optional[Dict]:
        """Get email by message ID."""
        try:
            endpoint = f'emails?message_id=eq.{message_id}&limit=1'
            result = await self._request('GET', endpoint)
            return result[0] if result else None
        except httpx.HTTPStatusError:
            return None
    
    async def get_recent_emails(self, limit: int = 10) -> List[Dict]:
        """Get recent emails."""
        try:
            endpoint = f'emails?order=received_at.desc&limit={limit}'
            return await self._request('GET', endpoint)
        except httpx.HTTPStatusError as e:
            raise ValueError(f"Failed to get recent emails: {e.response.text}")
    
    async def get_email_count(self) -> int:
        """Get total email count."""
        try:
            headers = {**self.headers, 'Prefer': 'count=exact'}
            url = urljoin(self.rest_url, 'emails?select=id')
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                
                # Extract count from Content-Range header
                content_range = response.headers.get('Content-Range', '')
                if '/' in content_range:
                    return int(content_range.split('/')[-1])
                return 0
        except httpx.HTTPStatusError:
            return 0
    
    async def test_connection(self) -> bool:
        """Test connection to Supabase."""
        try:
            await self._request('GET', 'emails?limit=1')
            return True
        except Exception:
            return False


class LightweightSupabaseDatabaseInterface:
    """Lightweight database interface using HTTP client."""
    
    def __init__(self):
        self.client: Optional[LightweightSupabaseClient] = None
        self._connected = False
        self.current_user_id = "00000000-0000-0000-0000-000000000000"  # Default user
    
    async def connect(self, connection_string: Optional[str] = None) -> None:
        """Connect using lightweight client."""
        try:
            self.client = LightweightSupabaseClient()
            # Test connection
            if await self.client.test_connection():
                self._connected = True
            else:
                raise ConnectionError("Connection test failed")
        except Exception as e:
            raise ConnectionError(f"Failed to connect: {str(e)}") from e
    
    async def store_email(self, email: ProcessedEmail) -> str:
        """Store email using lightweight client."""
        if not self._connected or not self.client:
            raise RuntimeError("Database not connected")
        
        # Convert ProcessedEmail to Supabase format
        email_data = {
            "id": email.id,
            "user_id": self.current_user_id,
            "message_id": email.email_data.message_id,
            "from_email": email.email_data.from_email,
            "to_emails": email.email_data.to_emails,
            "cc_emails": email.email_data.cc_emails or [],
            "bcc_emails": email.email_data.bcc_emails or [],
            "subject": email.email_data.subject,
            "text_body": email.email_data.text_body,
            "html_body": email.email_data.html_body,
            "received_at": email.email_data.received_at.isoformat(),
            "headers": email.email_data.headers or {},
            "status": email.status.value if hasattr(email.status, "value") else email.status,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Add analysis data if present
        if email.analysis:
            email_data.update({
                "urgency_score": email.analysis.urgency_score,
                "urgency_level": email.analysis.urgency_level,
                "sentiment": email.analysis.sentiment,
                "confidence": email.analysis.confidence,
                "keywords": email.analysis.keywords or []
            })
        
        return await self.client.insert_email(email_data)
    
    async def get_recent_emails(self, limit: int = 10) -> List[Dict]:
        """Get recent emails."""
        if not self._connected or not self.client:
            raise RuntimeError("Database not connected")
        
        return await self.client.get_recent_emails(limit)
    
    async def get_email_count(self) -> int:
        """Get email count."""
        if not self._connected or not self.client:
            raise RuntimeError("Database not connected")
        
        return await self.client.get_email_count()
    
    async def disconnect(self) -> None:
        """Disconnect."""
        self._connected = False
        self.client = None
