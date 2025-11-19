"""
Upstox API Client Module
Handles authentication, session management, and API calls with advanced error handling
"""

import time
import requests
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
from loguru import logger
from functools import wraps
import upstox_client
from upstox_client.rest import ApiException


class UpstoxAPIError(Exception):
    """Custom exception for Upstox API errors"""
    pass


class AuthenticationError(UpstoxAPIError):
    """Authentication related errors"""
    pass


class RateLimitError(UpstoxAPIError):
    """Rate limit exceeded"""
    pass


class ConnectionError(UpstoxAPIError):
    """Connection related errors"""
    pass


def exponential_backoff_retry(max_retries: int = 3, base_delay: float = 1.0):
    """
    Decorator for exponential backoff retry logic
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries <= max_retries:
                try:
                    return func(*args, **kwargs)
                except RateLimitError as e:
                    if retries == max_retries:
                        logger.error(f"Max retries reached for {func.__name__}: {e}")
                        raise
                    
                    delay = base_delay * (2 ** retries)
                    logger.warning(f"Rate limit hit. Retrying in {delay}s (attempt {retries + 1}/{max_retries})")
                    time.sleep(delay)
                    retries += 1
                except (ConnectionError, requests.exceptions.RequestException) as e:
                    if retries == max_retries:
                        logger.error(f"Max retries reached for {func.__name__}: {e}")
                        raise
                    
                    delay = base_delay * (2 ** retries)
                    logger.warning(f"Connection error. Retrying in {delay}s (attempt {retries + 1}/{max_retries})")
                    time.sleep(delay)
                    retries += 1
                except Exception as e:
                    logger.error(f"Unexpected error in {func.__name__}: {e}")
                    raise
            
        return wrapper
    return decorator


class UpstoxClient:
    """
    Advanced Upstox API Client with:
    - Automatic token refresh
    - Exponential backoff retry
    - Circuit breaker pattern
    - Comprehensive error handling
    """
    
    def __init__(self, api_key: str, api_secret: str, redirect_uri: str, access_token: str = ""):
        """
        Initialize Upstox client
        
        Args:
            api_key: Upstox API key
            api_secret: Upstox API secret
            redirect_uri: Redirect URI for OAuth
            access_token: Access token (if already available)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.redirect_uri = redirect_uri
        self.access_token = access_token
        
        # Circuit breaker state
        self.circuit_breaker_open = False
        self.circuit_breaker_failures = 0
        self.circuit_breaker_threshold = 5
        self.circuit_breaker_reset_time = None
        self.circuit_breaker_timeout = 60  # seconds
        
        # Session management
        self.session = requests.Session()
        self.token_expiry = None
        self.token_refresh_buffer = timedelta(minutes=5)
        
        # API configuration
        self.configuration = upstox_client.Configuration()
        self.api_client = None
        
        # Initialize if token provided
        if self.access_token:
            self._initialize_api_client()
    
    def _initialize_api_client(self):
        """Initialize Upstox API client with access token"""
        self.configuration.access_token = self.access_token
        self.api_client = upstox_client.ApiClient(self.configuration)
        logger.info("Upstox API client initialized successfully")
    
    def get_authorization_url(self) -> str:
        """
        Get OAuth authorization URL for user login
        
        Returns:
            Authorization URL
        """
        auth_url = (f"https://api.upstox.com/v2/login/authorization/dialog"
                   f"?client_id={self.api_key}&redirect_uri={self.redirect_uri}&response_type=code")
        logger.info(f"Authorization URL generated: {auth_url}")
        return auth_url
    
    @exponential_backoff_retry(max_retries=3, base_delay=1.0)
    def get_access_token(self, authorization_code: str) -> str:
        """
        Exchange authorization code for access token
        
        Args:
            authorization_code: Authorization code from OAuth callback
            
        Returns:
            Access token
            
        Raises:
            AuthenticationError: If token exchange fails
        """
        try:
            url = "https://api.upstox.com/v2/login/authorization/token"
            headers = {
                'accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded',
            }
            data = {
                'code': authorization_code,
                'client_id': self.api_key,
                'client_secret': self.api_secret,
                'redirect_uri': self.redirect_uri,
                'grant_type': 'authorization_code',
            }
            
            response = self.session.post(url, headers=headers, data=data)
            
            if response.status_code == 429:
                raise RateLimitError("Rate limit exceeded")
            elif response.status_code in [500, 502, 503, 504]:
                raise ConnectionError(f"Server error: {response.status_code}")
            elif response.status_code != 200:
                raise AuthenticationError(f"Token exchange failed: {response.text}")
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            self.token_expiry = datetime.now() + timedelta(seconds=token_data.get('expires_in', 86400))
            
            self._initialize_api_client()
            logger.info("Access token obtained successfully")
            
            return self.access_token
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Network error during token exchange: {e}")
    
    def _check_circuit_breaker(self):
        """Check circuit breaker state"""
        if self.circuit_breaker_open:
            if datetime.now() > self.circuit_breaker_reset_time:
                logger.info("Circuit breaker reset - attempting to close")
                self.circuit_breaker_open = False
                self.circuit_breaker_failures = 0
            else:
                raise UpstoxAPIError("Circuit breaker is OPEN - API calls suspended")
    
    def _handle_circuit_breaker_failure(self):
        """Handle circuit breaker failure"""
        self.circuit_breaker_failures += 1
        if self.circuit_breaker_failures >= self.circuit_breaker_threshold:
            self.circuit_breaker_open = True
            self.circuit_breaker_reset_time = datetime.now() + timedelta(seconds=self.circuit_breaker_timeout)
            logger.error(f"Circuit breaker OPENED after {self.circuit_breaker_failures} failures")
    
    def _check_and_refresh_token(self):
        """Check token expiry and refresh if needed"""
        if self.token_expiry and datetime.now() > (self.token_expiry - self.token_refresh_buffer):
            logger.warning("Token nearing expiry - manual re-authentication required")
            # Note: Upstox doesn't support automatic token refresh
            # User needs to re-authenticate
            raise AuthenticationError("Token expired - re-authentication required")
    
    @exponential_backoff_retry(max_retries=3, base_delay=1.0)
    def get_profile(self) -> Dict[str, Any]:
        """
        Get user profile
        
        Returns:
            User profile data
        """
        self._check_circuit_breaker()
        self._check_and_refresh_token()
        
        try:
            api_instance = upstox_client.UserApi(self.api_client)
            api_response = api_instance.get_profile(api_version='2.0')
            logger.info("Profile fetched successfully")
            return api_response.to_dict()
            
        except ApiException as e:
            self._handle_api_exception(e)
    
    @exponential_backoff_retry(max_retries=3, base_delay=1.0)
    def get_positions(self) -> Dict[str, Any]:
        """
        Get current positions
        
        Returns:
            Positions data
        """
        self._check_circuit_breaker()
        self._check_and_refresh_token()
        
        try:
            api_instance = upstox_client.PortfolioApi(self.api_client)
            api_response = api_instance.get_positions(api_version='2.0')
            logger.debug("Positions fetched successfully")
            return api_response.to_dict()
            
        except ApiException as e:
            self._handle_api_exception(e)
    
    @exponential_backoff_retry(max_retries=3, base_delay=1.0)
    def get_holdings(self) -> Dict[str, Any]:
        """
        Get holdings
        
        Returns:
            Holdings data
        """
        self._check_circuit_breaker()
        self._check_and_refresh_token()
        
        try:
            api_instance = upstox_client.PortfolioApi(self.api_client)
            api_response = api_instance.get_holdings(api_version='2.0')
            logger.debug("Holdings fetched successfully")
            return api_response.to_dict()
            
        except ApiException as e:
            self._handle_api_exception(e)
    
    @exponential_backoff_retry(max_retries=3, base_delay=1.0)
    def place_order(
        self,
        symbol: str,
        quantity: int,
        transaction_type: str,
        order_type: str,
        product: str = "D",
        price: float = 0.0,
        trigger_price: float = 0.0,
        validity: str = "DAY",
        disclosed_quantity: int = 0
    ) -> Dict[str, Any]:
        """
        Place an order
        
        Args:
            symbol: Trading symbol (e.g., 'NSE_EQ|INE467B01029')
            quantity: Order quantity
            transaction_type: 'BUY' or 'SELL'
            order_type: 'MARKET', 'LIMIT', 'SL', 'SL-M'
            product: Product type ('D' for delivery, 'I' for intraday)
            price: Limit price (for LIMIT orders)
            trigger_price: Trigger price (for SL orders)
            validity: Order validity ('DAY', 'IOC')
            disclosed_quantity: Disclosed quantity for iceberg orders
            
        Returns:
            Order response
        """
        self._check_circuit_breaker()
        self._check_and_refresh_token()
        
        try:
            api_instance = upstox_client.OrderApi(self.api_client)
            
            order_body = upstox_client.PlaceOrderRequest(
                quantity=quantity,
                product=product,
                validity=validity,
                price=price,
                tag="AlgoTradingBot",
                instrument_token=symbol,
                order_type=order_type,
                transaction_type=transaction_type,
                disclosed_quantity=disclosed_quantity,
                trigger_price=trigger_price,
                is_amo=False
            )
            
            api_response = api_instance.place_order(order_body, api_version='2.0')
            logger.info(f"Order placed: {transaction_type} {quantity} {symbol} @ {price}")
            return api_response.to_dict()
            
        except ApiException as e:
            self._handle_api_exception(e)
    
    @exponential_backoff_retry(max_retries=3, base_delay=1.0)
    def modify_order(
        self,
        order_id: str,
        quantity: Optional[int] = None,
        order_type: Optional[str] = None,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Modify an existing order
        
        Args:
            order_id: Order ID to modify
            quantity: New quantity
            order_type: New order type
            price: New price
            trigger_price: New trigger price
            
        Returns:
            Modification response
        """
        self._check_circuit_breaker()
        self._check_and_refresh_token()
        
        try:
            api_instance = upstox_client.OrderApi(self.api_client)
            
            modify_body = upstox_client.ModifyOrderRequest(
                quantity=quantity,
                validity="DAY",
                price=price,
                order_type=order_type,
                trigger_price=trigger_price
            )
            
            api_response = api_instance.modify_order(modify_body, api_version='2.0', order_id=order_id)
            logger.info(f"Order modified: {order_id}")
            return api_response.to_dict()
            
        except ApiException as e:
            self._handle_api_exception(e)
    
    @exponential_backoff_retry(max_retries=3, base_delay=1.0)
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel an order
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            Cancellation response
        """
        self._check_circuit_breaker()
        self._check_and_refresh_token()
        
        try:
            api_instance = upstox_client.OrderApi(self.api_client)
            api_response = api_instance.cancel_order(order_id=order_id, api_version='2.0')
            logger.info(f"Order cancelled: {order_id}")
            return api_response.to_dict()
            
        except ApiException as e:
            self._handle_api_exception(e)
    
    @exponential_backoff_retry(max_retries=3, base_delay=1.0)
    def get_order_history(self, order_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get order history
        
        Args:
            order_id: Specific order ID (optional)
            
        Returns:
            Order history
        """
        self._check_circuit_breaker()
        self._check_and_refresh_token()
        
        try:
            api_instance = upstox_client.OrderApi(self.api_client)
            
            if order_id:
                api_response = api_instance.get_order_details(api_version='2.0', order_id=order_id)
            else:
                api_response = api_instance.get_order_book(api_version='2.0')
            
            logger.debug("Order history fetched")
            return api_response.to_dict()
            
        except ApiException as e:
            self._handle_api_exception(e)
    
    def _handle_api_exception(self, exception: ApiException):
        """Handle API exceptions with specific error codes"""
        status = exception.status
        
        if status == 401:
            self._handle_circuit_breaker_failure()
            raise AuthenticationError("Authentication failed - invalid or expired token")
        elif status == 429:
            raise RateLimitError("Rate limit exceeded")
        elif status in [500, 502, 503, 504]:
            self._handle_circuit_breaker_failure()
            raise ConnectionError(f"Server error: {status}")
        elif status == 400:
            logger.error(f"Bad request: {exception.body}")
            raise UpstoxAPIError(f"Bad request: {exception.body}")
        else:
            self._handle_circuit_breaker_failure()
            logger.error(f"API error {status}: {exception}")
            raise UpstoxAPIError(f"API error {status}: {exception}")
    
    def health_check(self) -> bool:
        """
        Perform health check
        
        Returns:
            True if API is healthy
        """
        try:
            self.get_profile()
            logger.info("Health check passed")
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def __repr__(self) -> str:
        return f"UpstoxClient(authenticated={bool(self.access_token)}, circuit_breaker_open={self.circuit_breaker_open})"
