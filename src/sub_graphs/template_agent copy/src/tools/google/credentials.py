"""Google API credentials handler."""

import os
import pickle
import logging
from typing import List, Optional
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from functools import lru_cache

logger = logging.getLogger(__name__)

class CredentialsHandler:
    """Handles Google API credentials."""
    
    def __init__(self, token_path: str = None, credentials_path: str = None):
        """Initialize credentials handler.
        
        Args:
            token_path: Path to token file
            credentials_path: Path to credentials file
        """
        # Get paths from environment variables or use provided paths
        self.token_path = token_path or os.getenv('GOOGLE_TOKEN_FILE', 'token.pickle')
        self.credentials_path = credentials_path or os.getenv('GOOGLE_CLIENT_SECRET_FILE', 'credentials.json')
        
        # Validate paths
        if not os.path.exists(self.credentials_path):
            raise FileNotFoundError(
                f"Google credentials file not found at {self.credentials_path}. "
                "Please set GOOGLE_CLIENT_SECRET_FILE environment variable to point to your credentials.json file."
            )
            
        # Create token directory if it doesn't exist
        token_dir = os.path.dirname(self.token_path)
        if token_dir:
            os.makedirs(token_dir, exist_ok=True)
            
        self.credentials = None
        
    def get_credentials(self, scopes: List[str]) -> Optional[Credentials]:
        """Get valid credentials.
        
        Args:
            scopes: List of required scopes
            
        Returns:
            Valid credentials or None
        """
        try:
            if os.path.exists(self.token_path):
                logger.debug(f"Loading existing token from {self.token_path}")
                with open(self.token_path, 'rb') as token:
                    self.credentials = pickle.load(token)
            
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    logger.debug("Refreshing expired credentials")
                    self.credentials.refresh(Request())
                else:
                    logger.debug(f"Creating new credentials flow with {self.credentials_path}")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, scopes)
                    self.credentials = flow.run_local_server(port=0)
                    
                logger.debug(f"Saving credentials to {self.token_path}")
                with open(self.token_path, 'wb') as token:
                    pickle.dump(self.credentials, token)
                    
            return self.credentials
        except Exception as e:
            logger.error(f"Error getting credentials: {e}")
            return None

@lru_cache(maxsize=1)
def get_credentials_handler() -> CredentialsHandler:
    """Get or create a singleton CredentialsHandler instance."""
    return CredentialsHandler()

def get_credentials(scopes: List[str] = None) -> Optional[Credentials]:
    """Get valid credentials using the singleton CredentialsHandler.
    
    Args:
        scopes: List of required scopes. If None, uses default scopes.
        
    Returns:
        Valid credentials or None
    """
    if scopes is None:
        scopes = [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.send',
            'https://www.googleapis.com/auth/calendar',
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/tasks',
            'https://www.googleapis.com/auth/contacts'
        ]
    return get_credentials_handler().get_credentials(scopes) 