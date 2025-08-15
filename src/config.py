"""Configuration management for Calendar Sync."""

import os
from typing import Dict, Any


class Config:
    """Configuration class for managing calendar sync settings."""
    
    def __init__(self):
        self.google_credentials_file = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
        self.google_token_file = os.getenv('GOOGLE_TOKEN_FILE', 'token.json')
        self.google_calendar_id = os.getenv('GOOGLE_CALENDAR_ID', 'primary')
        
        self.icloud_username = os.getenv('ICLOUD_USERNAME')
        self.icloud_password = os.getenv('ICLOUD_PASSWORD')
        self.icloud_server = os.getenv('ICLOUD_SERVER', 'https://caldav.icloud.com')
        
        self.sync_direction = os.getenv('SYNC_DIRECTION', 'both')  # 'both', 'google_to_icloud', 'icloud_to_google'
        self.sync_frequency = int(os.getenv('SYNC_FREQUENCY', '60'))  # minutes
        self.timezone = os.getenv('TIMEZONE', 'America/New_York')  # Default timezone
        self.source_of_truth = os.getenv('SOURCE_OF_TRUTH', 'auto')  # 'auto', 'google', 'icloud'
        
        self.validate_config()
    
    def validate_config(self):
        """Validate the configuration settings."""
        if not self.icloud_username:
            raise ValueError("ICLOUD_USERNAME environment variable is required")
        
        if not self.icloud_password:
            raise ValueError("ICLOUD_PASSWORD environment variable is required")
        
        if self.sync_direction not in ['both', 'google_to_icloud', 'icloud_to_google']:
            raise ValueError("SYNC_DIRECTION must be 'both', 'google_to_icloud', or 'icloud_to_google'")
    
    def get_google_scopes(self) -> list:
        """Get the required Google Calendar API scopes."""
        return ['https://www.googleapis.com/auth/calendar']
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary (excluding sensitive data)."""
        return {
            'google_calendar_id': self.google_calendar_id,
            'icloud_server': self.icloud_server,
            'sync_direction': self.sync_direction,
            'sync_frequency': self.sync_frequency
        }
