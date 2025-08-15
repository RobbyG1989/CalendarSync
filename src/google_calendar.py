"""Google Calendar client for calendar synchronization."""

import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .config import Config


class GoogleCalendarClient:
    """Client for interacting with Google Calendar API."""
    
    def __init__(self, config: Config):
        self.config = config
        self.service = None
        self.credentials = None
        
    def authenticate(self) -> None:
        """Authenticate with Google Calendar API."""
        creds = None
        
        # Load existing token
        if os.path.exists(self.config.google_token_file):
            creds = Credentials.from_authorized_user_file(
                self.config.google_token_file, 
                self.config.get_google_scopes()
            )
        
        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.config.google_credentials_file):
                    raise FileNotFoundError(
                        f"Google credentials file not found: {self.config.google_credentials_file}\n"
                        "Please download your OAuth 2.0 credentials from Google Cloud Console"
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.config.google_credentials_file,
                    self.config.get_google_scopes()
                )
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(self.config.google_token_file, 'w') as token:
                token.write(creds.to_json())
        
        self.credentials = creds
        self.service = build('calendar', 'v3', credentials=creds)
    
    def list_calendars(self) -> List[Dict[str, Any]]:
        """List all available calendars."""
        if not self.service:
            self.authenticate()
        
        try:
            calendars_result = self.service.calendarList().list().execute()
            calendars = calendars_result.get('items', [])
            return calendars
        except HttpError as error:
            raise Exception(f"Failed to list Google calendars: {error}")
    
    def get_events(self, start_time: datetime, end_time: datetime, 
                   calendar_id: str = None) -> List[Dict[str, Any]]:
        """Get events from Google Calendar within the specified time range."""
        if not self.service:
            self.authenticate()
        
        if not calendar_id:
            calendar_id = self.config.google_calendar_id
        
        try:
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=start_time.isoformat() + 'Z',
                timeMax=end_time.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            return events
        except HttpError as error:
            raise Exception(f"Failed to get Google Calendar events: {error}")
    
    def create_event(self, event_data: Dict[str, Any], 
                     calendar_id: str = None) -> Dict[str, Any]:
        """Create a new event in Google Calendar."""
        if not self.service:
            self.authenticate()
        
        if not calendar_id:
            calendar_id = self.config.google_calendar_id
        
        try:
            event = self.service.events().insert(
                calendarId=calendar_id,
                body=event_data
            ).execute()
            return event
        except HttpError as error:
            raise Exception(f"Failed to create Google Calendar event: {error}")
    
    def update_event(self, event_id: str, event_data: Dict[str, Any],
                     calendar_id: str = None) -> Dict[str, Any]:
        """Update an existing event in Google Calendar."""
        if not self.service:
            self.authenticate()
        
        if not calendar_id:
            calendar_id = self.config.google_calendar_id
        
        try:
            event = self.service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event_data
            ).execute()
            return event
        except HttpError as error:
            raise Exception(f"Failed to update Google Calendar event: {error}")
    
    def delete_event(self, event_id: str, calendar_id: str = None) -> None:
        """Delete an event from Google Calendar."""
        if not self.service:
            self.authenticate()
        
        if not calendar_id:
            calendar_id = self.config.google_calendar_id
        
        try:
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
        except HttpError as error:
            raise Exception(f"Failed to delete Google Calendar event: {error}")
    
    def format_event_for_sync(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Format a Google Calendar event for synchronization."""
        formatted_event = {
            'id': event.get('id'),
            'summary': event.get('summary', ''),
            'description': event.get('description', ''),
            'location': event.get('location', ''),
            'start': self._parse_datetime(event.get('start')),
            'end': self._parse_datetime(event.get('end')),
            'all_day': 'date' in event.get('start', {}),
            'source': 'google',
            'raw_data': event
        }
        return formatted_event
    
    def _parse_datetime(self, dt_obj: Dict[str, Any]) -> Optional[datetime]:
        """Parse datetime from Google Calendar format."""
        if not dt_obj:
            return None
        
        if 'dateTime' in dt_obj:
            return datetime.fromisoformat(dt_obj['dateTime'].replace('Z', '+00:00'))
        elif 'date' in dt_obj:
            return datetime.fromisoformat(dt_obj['date'])
        
        return None
