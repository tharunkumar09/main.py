"""
Session Management with Token Refresh Logic for Upstox API
Handles authentication, token refresh, and session persistence
"""

import time
import json
import requests
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from loguru import logger
from pathlib import Path

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from config import (
    UPSTOX_API_KEY, UPSTOX_API_SECRET, UPSTOX_REDIRECT_URI, UPSTOX_ACCESS_TOKEN,
    UPSTOX_SANDBOX_MODE, UPSTOX_API_BASE_URL, UPSTOX_AUTH_BASE_URL, BASE_DIR
)


class SessionManager:
    """
    Manages Upstox API authentication and session tokens.
    Implements automatic token refresh with exponential backoff.
    Supports both sandbox (paper trading) and production modes.
    """
    
    BASE_URL = UPSTOX_API_BASE_URL
    TOKEN_URL = f"{BASE_URL}/login/authorization/token"
    PROFILE_URL = f"{BASE_URL}/user/profile"
    TOKEN_FILE = BASE_DIR / ".upstox_token.json"
    SANDBOX_MODE = UPSTOX_SANDBOX_MODE
    
    def __init__(self, api_key: str = None, api_secret: str = None, 
                 redirect_uri: str = None, access_token: str = None):
        """
        Initialize Session Manager
        
        Args:
            api_key: Upstox API key
            api_secret: Upstox API secret
            redirect_uri: Redirect URI for OAuth
            access_token: Pre-existing access token (optional)
        """
        self.api_key = api_key or UPSTOX_API_KEY
        self.api_secret = api_secret or UPSTOX_API_SECRET
        self.redirect_uri = redirect_uri or UPSTOX_REDIRECT_URI
        self.access_token = access_token or UPSTOX_ACCESS_TOKEN
        
        self.token_expiry: Optional[datetime] = None
        self.refresh_token: Optional[str] = None
        self.session = requests.Session()
        
        # Load saved token if exists
        self._load_token()
        
        # Validate and refresh token if needed
        if self.access_token:
            self._validate_token()
    
    def _load_token(self) -> None:
        """Load token from file if exists"""
        if self.TOKEN_FILE.exists():
            try:
                with open(self.TOKEN_FILE, 'r') as f:
                    token_data = json.load(f)
                    self.access_token = token_data.get('access_token')
                    self.refresh_token = token_data.get('refresh_token')
                    expiry_str = token_data.get('expiry')
                    if expiry_str:
                        self.token_expiry = datetime.fromisoformat(expiry_str)
                logger.info("Loaded token from file")
            except Exception as e:
                logger.error(f"Error loading token: {e}")
    
    def _save_token(self) -> None:
        """Save token to file"""
        try:
            token_data = {
                'access_token': self.access_token,
                'refresh_token': self.refresh_token,
                'expiry': self.token_expiry.isoformat() if self.token_expiry else None
            }
            with open(self.TOKEN_FILE, 'w') as f:
                json.dump(token_data, f)
            logger.info("Token saved to file")
        except Exception as e:
            logger.error(f"Error saving token: {e}")
    
    def get_authorization_url(self) -> str:
        """
        Generate authorization URL for OAuth flow
        
        Returns:
            Authorization URL
        """
        mode_text = "SANDBOX" if self.SANDBOX_MODE else "PRODUCTION"
        logger.info(f"Generating authorization URL for {mode_text} mode")
        
        auth_url = (
            f"{UPSTOX_AUTH_BASE_URL}/oauth/authorize?"
            f"response_type=code&"
            f"client_id={self.api_key}&"
            f"redirect_uri={self.redirect_uri}"
        )
        return auth_url
    
    def get_access_token_from_code(self, authorization_code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token
        
        Args:
            authorization_code: Authorization code from OAuth callback
            
        Returns:
            Token response dictionary
        """
        try:
            payload = {
                "code": authorization_code,
                "client_id": self.api_key,
                "client_secret": self.api_secret,
                "redirect_uri": self.redirect_uri,
                "grant_type": "authorization_code"
            }
            
            response = requests.post(self.TOKEN_URL, json=payload)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data.get('access_token')
            self.refresh_token = token_data.get('refresh_token')
            
            # Set expiry (typically 24 hours, but using 23 hours for safety)
            expires_in = token_data.get('expires_in', 86400)
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in - 3600)
            
            self._save_token()
            logger.info("Access token obtained successfully")
            
            return token_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting access token: {e}")
            raise
    
    def refresh_access_token(self) -> bool:
        """
        Refresh the access token using refresh token
        
        Returns:
            True if refresh successful, False otherwise
        """
        if not self.refresh_token:
            logger.warning("No refresh token available")
            return False
        
        try:
            payload = {
                "refresh_token": self.refresh_token,
                "client_id": self.api_key,
                "client_secret": self.api_secret,
                "grant_type": "refresh_token"
            }
            
            response = requests.post(self.TOKEN_URL, json=payload)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data.get('access_token')
            self.refresh_token = token_data.get('refresh_token', self.refresh_token)
            
            expires_in = token_data.get('expires_in', 86400)
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in - 3600)
            
            self._save_token()
            logger.info("Access token refreshed successfully")
            
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error refreshing access token: {e}")
            return False
    
    def _validate_token(self) -> bool:
        """
        Validate token by making a test API call
        
        Returns:
            True if token is valid, False otherwise
        """
        if not self.access_token:
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = requests.get(self.PROFILE_URL, headers=headers)
            
            if response.status_code == 401:
                logger.warning("Token expired, attempting refresh")
                return self.refresh_access_token()
            
            response.raise_for_status()
            logger.info("Token validated successfully")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Token validation failed: {e}")
            return False
    
    def is_token_valid(self) -> bool:
        """
        Check if token is valid and not expired
        
        Returns:
            True if token is valid, False otherwise
        """
        if not self.access_token:
            return False
        
        # Check if token is expired or will expire soon (within 5 minutes)
        if self.token_expiry:
            if datetime.now() >= (self.token_expiry - timedelta(minutes=5)):
                logger.info("Token expiring soon, refreshing...")
                return self.refresh_access_token()
        
        return True
    
    def get_headers(self) -> Dict[str, str]:
        """
        Get authorization headers for API requests
        
        Returns:
            Dictionary with Authorization header
        """
        if not self.is_token_valid():
            raise Exception("Invalid or expired access token")
        
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"
        }
    
    def get_session(self) -> requests.Session:
        """
        Get authenticated requests session
        
        Returns:
            Authenticated requests session
        """
        self.session.headers.update(self.get_headers())
        return self.session
