"""
Authentication and Session Management with token refresh logic
"""
import time
import requests
from typing import Optional, Dict
from datetime import datetime, timedelta
import logging
from trading_bot.config.settings import settings

logger = logging.getLogger(__name__)


class UpstoxAuth:
    """Handles Upstox API authentication and token management"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        access_token: Optional[str] = None
    ):
        self.api_key = api_key or settings.UPSTOX_API_KEY
        self.api_secret = api_secret or settings.UPSTOX_API_SECRET
        self.redirect_uri = redirect_uri or settings.UPSTOX_REDIRECT_URI
        self.base_url = settings.API_BASE_URL
        
        self.access_token: Optional[str] = access_token or settings.UPSTOX_ACCESS_TOKEN
        self.token_expiry: Optional[datetime] = None
        self.refresh_token: Optional[str] = None
        
        # Token expiry is typically 24 hours, but we'll refresh 1 hour before
        self.token_buffer_minutes = 60
    
    def get_auth_url(self) -> str:
        """Generate authorization URL for OAuth flow"""
        auth_url = (
            f"https://account.upstox.com/oauth/authorize"
            f"?response_type=code"
            f"&client_id={self.api_key}"
            f"&redirect_uri={self.redirect_uri}"
        )
        return auth_url
    
    def get_access_token_from_code(self, auth_code: str) -> Dict:
        """Exchange authorization code for access token"""
        url = f"{self.base_url}/login/authorization/token"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        data = {
            "code": auth_code,
            "client_id": self.api_key,
            "client_secret": self.api_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code"
        }
        
        try:
            response = requests.post(url, headers=headers, data=data, timeout=10)
            response.raise_for_status()
            token_data = response.json()
            
            self.access_token = token_data.get("access_token")
            self.refresh_token = token_data.get("refresh_token")
            expires_in = token_data.get("expires_in", 86400)  # Default 24 hours
            
            # Set token expiry time
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in - self.token_buffer_minutes * 60)
            
            logger.info("Successfully obtained access token")
            return token_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get access token: {e}")
            raise
    
    def refresh_access_token(self) -> bool:
        """Refresh the access token using refresh token"""
        if not self.refresh_token:
            logger.error("No refresh token available")
            return False
        
        url = f"{self.base_url}/login/authorization/token"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.api_key,
            "client_secret": self.api_secret
        }
        
        try:
            response = requests.post(url, headers=headers, data=data, timeout=10)
            response.raise_for_status()
            token_data = response.json()
            
            self.access_token = token_data.get("access_token")
            new_refresh_token = token_data.get("refresh_token")
            if new_refresh_token:
                self.refresh_token = new_refresh_token
            
            expires_in = token_data.get("expires_in", 86400)
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in - self.token_buffer_minutes * 60)
            
            logger.info("Successfully refreshed access token")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to refresh access token: {e}")
            return False
    
    def get_valid_token(self) -> Optional[str]:
        """Get a valid access token, refreshing if necessary"""
        if not self.access_token:
            logger.error("No access token available")
            return None
        
        # Check if token needs refresh
        if self.token_expiry and datetime.now() >= self.token_expiry:
            logger.info("Access token expired, refreshing...")
            if not self.refresh_access_token():
                logger.error("Failed to refresh token")
                return None
        
        return self.access_token
    
    def get_headers(self) -> Dict[str, str]:
        """Get headers with valid access token"""
        token = self.get_valid_token()
        if not token:
            raise ValueError("No valid access token available")
        
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}"
        }
    
    def is_authenticated(self) -> bool:
        """Check if we have a valid authentication"""
        return self.get_valid_token() is not None
