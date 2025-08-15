"""iCloud Calendar client using CalDAV protocol."""

import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from urllib.parse import urlparse

import caldav
from caldav import DAVClient, Calendar, Event
import pytz
from dateutil import parser

from .config import Config


class iCloudCalendarClient:
    """Client for interacting with iCloud Calendar via CalDAV."""
    
    def __init__(self, config: Config):
        self.config = config
        self.client = None
        self.principal = None
        self.calendars = None
        
    def authenticate(self) -> None:
        """Authenticate with iCloud CalDAV server."""
        try:
            self.client = DAVClient(
                url=self.config.icloud_server,
                username=self.config.icloud_username,
                password=self.config.icloud_password
            )
            
            # Test the connection
            self.principal = self.client.principal()
            self.calendars = self.principal.calendars()
            
            if not self.calendars:
                raise Exception("No calendars found in iCloud account")
                
        except Exception as e:
            raise Exception(f"Failed to authenticate with iCloud: {str(e)}")
    
    def list_calendars(self) -> List[Dict[str, Any]]:
        """List all available calendars."""
        if not self.calendars:
            self.authenticate()
        
        calendar_list = []
        for calendar in self.calendars:
            try:
                calendar_info = {
                    'id': str(calendar.url),
                    'name': calendar.name,
                    'color': getattr(calendar, 'color', None),
                    'description': getattr(calendar, 'description', ''),
                }
                calendar_list.append(calendar_info)
            except Exception as e:
                print(f"Warning: Could not retrieve info for calendar: {e}")
                
        return calendar_list
    
    def get_default_calendar(self) -> Calendar:
        """Get the default calendar for operations."""
        if not self.calendars:
            self.authenticate()
        
        # Return the first available calendar
        # In a real implementation, you might want to let users configure this
        return self.calendars[0]
    
    def get_events(self, start_time: datetime, end_time: datetime,
                   calendar: Calendar = None) -> List[Dict[str, Any]]:
        """Get events from iCloud Calendar within the specified time range."""
        if not calendar:
            calendar = self.get_default_calendar()
        
        try:
            # CalDAV search for events in the time range
            events = calendar.search(
                start=start_time,
                end=end_time,
                event=True,
                expand=True
            )
            
            formatted_events = []
            for event in events:
                try:
                    formatted_event = self.format_event_for_sync(event)
                    if formatted_event:
                        formatted_events.append(formatted_event)
                except Exception as e:
                    print(f"Warning: Could not parse event: {e}")
                    
            return formatted_events
            
        except Exception as e:
            raise Exception(f"Failed to get iCloud Calendar events: {str(e)}")
    
    def create_event(self, event_data: Dict[str, Any],
                     calendar: Calendar = None) -> Event:
        """Create a new event in iCloud Calendar."""
        if not calendar:
            calendar = self.get_default_calendar()
        
        try:
            # Convert event data to iCalendar format
            ical_data = self._create_ical_event(event_data)
            
            # Create the event
            event = calendar.save_event(ical_data)
            return event
            
        except Exception as e:
            raise Exception(f"Failed to create iCloud Calendar event: {str(e)}")
    
    def update_event(self, event: Event, event_data: Dict[str, Any]) -> Event:
        """Update an existing event in iCloud Calendar."""
        try:
            # Get the current event data
            current_ical = event.data
            
            # Update with new data
            updated_ical = self._update_ical_event(current_ical, event_data)
            
            # Save the updated event
            event.data = updated_ical
            event.save()
            return event
            
        except Exception as e:
            raise Exception(f"Failed to update iCloud Calendar event: {str(e)}")
    
    def delete_event(self, event: Event) -> None:
        """Delete an event from iCloud Calendar."""
        try:
            event.delete()
        except Exception as e:
            raise Exception(f"Failed to delete iCloud Calendar event: {str(e)}")
    
    def format_event_for_sync(self, event: Event) -> Optional[Dict[str, Any]]:
        """Format an iCloud Calendar event for synchronization."""
        try:
            # Parse the iCalendar data
            ical_data = event.data
            
            # Extract basic information using regex patterns
            # This is a simplified parser - in production, consider using a proper iCalendar library
            summary = self._extract_ical_field(ical_data, 'SUMMARY')
            description = self._extract_ical_field(ical_data, 'DESCRIPTION')
            location = self._extract_ical_field(ical_data, 'LOCATION')
            
            dtstart = self._extract_ical_field(ical_data, 'DTSTART')
            dtend = self._extract_ical_field(ical_data, 'DTEND')
            
            # Parse dates
            start_dt = self._parse_ical_datetime(dtstart) if dtstart else None
            end_dt = self._parse_ical_datetime(dtend) if dtend else None
            
            # Check if it's an all-day event
            all_day = dtstart and 'T' not in dtstart if dtstart else False
            
            formatted_event = {
                'id': str(event.url),
                'summary': summary or '',
                'description': description or '',
                'location': location or '',
                'start': start_dt,
                'end': end_dt,
                'all_day': all_day,
                'source': 'icloud',
                'raw_data': ical_data
            }
            
            return formatted_event
            
        except Exception as e:
            print(f"Error formatting iCloud event: {e}")
            return None
    
    def _extract_ical_field(self, ical_data: str, field_name: str) -> Optional[str]:
        """Extract a field value from iCalendar data."""
        pattern = rf'^{field_name}[^:]*:(.*)$'
        match = re.search(pattern, ical_data, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return None
    
    def _parse_ical_datetime(self, dt_string: str) -> Optional[datetime]:
        """Parse an iCalendar datetime string."""
        if not dt_string:
            return None
        
        try:
            # Handle timezone info
            if 'TZID=' in dt_string:
                # Extract timezone and datetime
                tz_match = re.search(r'TZID=([^:]+):', dt_string)
                if tz_match:
                    dt_part = dt_string.split(':', 1)[1]
                else:
                    dt_part = dt_string
            else:
                dt_part = dt_string.split(':', 1)[-1]
            
            # Parse the datetime
            if 'T' in dt_part:
                # DateTime format
                dt_part = dt_part.replace('Z', '')  # Remove Z suffix
                return parser.parse(dt_part)
            else:
                # Date format (all-day event)
                return datetime.strptime(dt_part, '%Y%m%d')
                
        except Exception as e:
            print(f"Error parsing datetime '{dt_string}': {e}")
            return None
    
    def _create_ical_event(self, event_data: Dict[str, Any]) -> str:
        """Create iCalendar format event data."""
        import uuid
        from datetime import timezone
        
        uid = str(uuid.uuid4())
        now = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        
        # Format start and end times
        if event_data.get('all_day'):
            dtstart = event_data['start'].strftime('%Y%m%d')
            dtend = event_data['end'].strftime('%Y%m%d')
            dtstart_line = f"DTSTART;VALUE=DATE:{dtstart}"
            dtend_line = f"DTEND;VALUE=DATE:{dtend}"
        else:
            # Preserve the original timezone instead of converting to UTC
            start_dt = event_data['start']
            end_dt = event_data['end']
            
            # If timezone-aware, use the timezone; otherwise treat as local time
            if start_dt.tzinfo is not None:
                # Format with timezone info preserved
                dtstart = start_dt.strftime('%Y%m%dT%H%M%S')
                dtend = end_dt.strftime('%Y%m%dT%H%M%S')
                dtstart_line = f"DTSTART:{dtstart}"
                dtend_line = f"DTEND:{dtend}"
            else:
                # Treat as local time, don't convert to UTC
                dtstart = start_dt.strftime('%Y%m%dT%H%M%S')
                dtend = end_dt.strftime('%Y%m%dT%H%M%S')
                dtstart_line = f"DTSTART:{dtstart}"
                dtend_line = f"DTEND:{dtend}"
        
        ical_data = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Calendar Sync//Calendar Sync//EN
BEGIN:VEVENT
UID:{uid}
DTSTAMP:{now}
CREATED:{now}
LAST-MODIFIED:{now}
SUMMARY:{event_data.get('summary', '')}
DESCRIPTION:{event_data.get('description', '')}
LOCATION:{event_data.get('location', '')}
{dtstart_line}
{dtend_line}
END:VEVENT
END:VCALENDAR"""
        
        return ical_data
    
    def _update_ical_event(self, current_ical: str, event_data: Dict[str, Any]) -> str:
        """Update iCalendar event data with new information."""
        # This is a simplified update - in production, use a proper iCalendar library
        updated_ical = current_ical
        
        # Update fields
        for field, value in [
            ('SUMMARY', event_data.get('summary', '')),
            ('DESCRIPTION', event_data.get('description', '')),
            ('LOCATION', event_data.get('location', ''))
        ]:
            pattern = rf'^{field}[^:]*:.*$'
            replacement = f"{field}:{value}"
            updated_ical = re.sub(pattern, replacement, updated_ical, flags=re.MULTILINE)
        
        return updated_ical
