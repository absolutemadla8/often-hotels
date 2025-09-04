import asyncio
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

import httpx
import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class TokenManager:
    """Manages API tokens with automatic refresh capabilities"""
    
    def __init__(self):
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._refresh_token: Optional[str] = None
        self._lock = asyncio.Lock()
    
    def set_tokens(self, access_token: str, expires_in: int, refresh_token: Optional[str] = None):
        """Set access token with expiry time"""
        self._access_token = access_token
        self._token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 60)  # 60s buffer
        if refresh_token:
            self._refresh_token = refresh_token
    
    def is_token_expired(self) -> bool:
        """Check if current token is expired or about to expire"""
        if not self._access_token or not self._token_expires_at:
            return True
        return datetime.utcnow() >= self._token_expires_at
    
    def get_access_token(self) -> Optional[str]:
        """Get current access token"""
        return self._access_token
    
    def get_refresh_token(self) -> Optional[str]:
        """Get refresh token"""
        return self._refresh_token


class BaseApiClient:
    """Base API client with token management and request handling"""
    
    def __init__(self, base_url: str, search_api_url: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.search_api_url = search_api_url.rstrip('/') if search_api_url else self.base_url
        self.token_manager = TokenManager()
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=60.0)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
    
    def get_default_headers(self, token: Optional[str] = None) -> Dict[str, str]:
        """Get default headers for requests"""
        headers = {
            'Accept': 'application/json',
            'Authorization-Type': 'external-service',
            'source': 'website'
        }
        
        if token:
            headers['Authorization'] = f'Bearer {token}'
        
        return headers
    
    async def make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        use_search_api: bool = False,
        retried: bool = False
    ) -> Dict[str, Any]:
        """Make HTTP request with automatic token refresh on 401"""
        
        if not self._client:
            raise HTTPException(status_code=500, detail="HTTP client not initialized")
        
        # Choose base URL
        base_url = self.search_api_url if use_search_api else self.base_url
        url = f"{base_url}{endpoint}"
        
        # Check if we need to refresh the token
        if self.token_manager.is_token_expired():
            await self.refresh_access_token()
        
        # Get the current token
        token = self.token_manager.get_access_token()
        
        headers = self.get_default_headers(token)
        if method.lower() in ['post', 'put', 'patch']:
            headers['Content-Type'] = 'application/json'
        
        try:
            if method.lower() == 'get':
                response = await self._client.get(url, headers=headers, params=params)
            elif method.lower() == 'post':
                response = await self._client.post(url, headers=headers, json=data)
            elif method.lower() == 'put':
                response = await self._client.put(url, headers=headers, json=data)
            elif method.lower() == 'delete':
                response = await self._client.delete(url, headers=headers, json=data)
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported HTTP method: {method}")
            
            # Handle token expiration
            if response.status_code == 401 and not retried:
                try:
                    response_data = response.json()
                    error_message = response_data.get('error', {}).get('message', '')
                    errors = response_data.get('error', {}).get('errors', [])
                    
                    # Check if the error is due to token expiration
                    if ('Unauthorized' in error_message or 
                        (isinstance(errors, list) and 'Token Expired. Unauthorized' in errors)):
                        
                        logger.info("API token expired. Attempting to refresh...")
                        
                        # Refresh token
                        await self.refresh_access_token()
                        
                        # Retry the request
                        return await self.make_request(method, endpoint, data, params, use_search_api, True)
                        
                except Exception as e:
                    logger.error(f"Failed to parse 401 response or refresh token: {e}")
                    raise HTTPException(status_code=401, detail="Authentication failed")
            
            # Handle other HTTP errors
            if response.status_code >= 400:
                try:
                    error_data = response.json()
                    error_msg = error_data.get('message', f'API request failed with status {response.status_code}')
                except:
                    error_msg = f'API request failed with status {response.status_code}'
                
                logger.error(f"API request failed: {method} {url} - {error_msg}")
                raise HTTPException(status_code=response.status_code, detail=error_msg)
            
            return response.json()
            
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in API request: {e}")
            raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
    
    async def refresh_access_token(self):
        """Refresh the access token - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement refresh_access_token method")