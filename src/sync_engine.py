"""Synchronization engine for calendar events."""

from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
import hashlib
import pytz

from .google_calendar import GoogleCalendarClient
from .icloud_calendar import iCloudCalendarClient
from .config import Config


class CalendarSyncEngine:
    """Engine for synchronizing events between Google Calendar and iCloud."""
    
    def __init__(self, google_client: GoogleCalendarClient, 
                 icloud_client: iCloudCalendarClient, config: Config):
        self.google_client = google_client
        self.icloud_client = icloud_client
        self.config = config
        
    def sync(self, start_date: datetime, end_date: datetime, 
             dry_run: bool = False) -> Dict[str, int]:
        """Perform calendar synchronization."""
        result = {
            'events_processed': 0,
            'events_created': 0,
            'events_updated': 0,
            'events_deleted': 0,
            'events_skipped': 0
        }
        
        try:
            # Get events from both calendars
            google_events = self.google_client.get_events(start_date, end_date)
            icloud_events = self.icloud_client.get_events(start_date, end_date)
            
            # Format events for comparison
            google_formatted = [
                self.google_client.format_event_for_sync(event) 
                for event in google_events
            ]
            icloud_formatted = [
                event for event in icloud_events if event is not None
            ]
            
            result['events_processed'] = len(google_formatted) + len(icloud_formatted)
            
            # Perform synchronization based on configuration
            if self.config.sync_direction == 'both':
                # For bidirectional sync, handle conflicts based on source of truth
                result = self._sync_bidirectional(google_formatted, icloud_formatted, dry_run)
            elif self.config.sync_direction == 'google_to_icloud':
                sync_stats = self._sync_events(
                    google_formatted, icloud_formatted, 
                    'google_to_icloud', dry_run
                )
                result['events_created'] += sync_stats['created']
                result['events_updated'] += sync_stats['updated']
                result['events_skipped'] += sync_stats.get('skipped', 0)
            elif self.config.sync_direction == 'icloud_to_google':
                sync_stats = self._sync_events(
                    icloud_formatted, google_formatted,
                    'icloud_to_google', dry_run
                )
                result['events_created'] += sync_stats['created']
                result['events_updated'] += sync_stats['updated']
                result['events_skipped'] += sync_stats.get('skipped', 0)
                
        except Exception as e:
            raise Exception(f"Sync failed: {str(e)}")
        
        return result
    
    def _sync_bidirectional(self, google_events: List[Dict[str, Any]], 
                           icloud_events: List[Dict[str, Any]], dry_run: bool) -> Dict[str, int]:
        """Handle bidirectional sync with conflict resolution."""
        result = {
            'events_processed': len(google_events) + len(icloud_events),
            'events_created': 0,
            'events_updated': 0,
            'events_deleted': 0,
            'events_skipped': 0
        }
        
        # Determine source of truth based on configuration
        if self.config.source_of_truth == 'auto':
            # Auto mode: use sync direction to determine source
            source_of_truth = 'google'  # Default to google for auto mode
        else:
            source_of_truth = self.config.source_of_truth
        
        if dry_run:
            print(f"Bidirectional sync mode - Source of truth: {source_of_truth.title()}")
            print()
        
        # Sync in both directions, but prioritize source of truth for conflicts
        if source_of_truth == 'google':
            # Google to iCloud first (Google wins conflicts)
            stats1 = self._sync_events(google_events, icloud_events, 'google_to_icloud', dry_run)
            # Then iCloud to Google (but skip conflicts)
            stats2 = self._sync_events(icloud_events, google_events, 'icloud_to_google', dry_run, avoid_conflicts=True)
        else:
            # iCloud to Google first (iCloud wins conflicts)
            stats1 = self._sync_events(icloud_events, google_events, 'icloud_to_google', dry_run)
            # Then Google to iCloud (but skip conflicts)
            stats2 = self._sync_events(google_events, icloud_events, 'google_to_icloud', dry_run, avoid_conflicts=True)
        
        # Combine statistics
        result['events_created'] = stats1['created'] + stats2['created']
        result['events_updated'] = stats1['updated'] + stats2['updated']
        result['events_skipped'] = stats1.get('skipped', 0) + stats2.get('skipped', 0)
        
        return result
    
    def _sync_events(self, source_events: List[Dict[str, Any]], 
                     target_events: List[Dict[str, Any]], 
                     direction: str, dry_run: bool, avoid_conflicts: bool = False) -> Dict[str, int]:
        """Sync events from source to target calendar."""
        stats = {'created': 0, 'updated': 0, 'skipped': 0}
        
        # Create a lookup for target events by content hash
        target_lookup = {}
        for event in target_events:
            content_hash = self._calculate_event_hash(event)
            target_lookup[content_hash] = event
        
        for source_event in source_events:
            content_hash = self._calculate_event_hash(source_event)
            
            # First check: exact hash match
            if content_hash in target_lookup:
                target_event = target_lookup[content_hash]
                if self._needs_update(source_event, target_event):
                    if not dry_run:
                        self._update_event_in_target(source_event, target_event, direction)
                    stats['updated'] += 1
                    
                    # Enhanced logging for updates
                    target_calendar = "iCloud" if direction == 'google_to_icloud' else "Google Calendar"
                    source_calendar = "Google Calendar" if direction == 'google_to_icloud' else "iCloud"
                    event_time = self._format_event_time(source_event)
                    
                    print(f"{'[DRY RUN] ' if dry_run else ''}Updating event: '{source_event['summary']}'")
                    print(f"  └─ From: {source_calendar} → To: {target_calendar}")
                    print(f"  └─ Time: {event_time}")
                    print()
                else:
                    stats['skipped'] += 1
                    print(f"{'[DRY RUN] ' if dry_run else ''}Skipping event: '{source_event['summary']}' (already exists and up to date)")
                continue
            
            # Second check: look for events that match description/summary but have different times (reschedules)
            rescheduled_event = self._find_rescheduled_event(source_event, target_events)
            if rescheduled_event:
                if avoid_conflicts:
                    # In conflict avoidance mode, skip rescheduling (other direction will handle it)
                    stats['skipped'] += 1
                    print(f"{'[DRY RUN] ' if dry_run else ''}Skipping reschedule: '{source_event['summary']}' (avoiding conflict)")
                    continue
                
                if not dry_run:
                    self._update_event_in_target(source_event, rescheduled_event, direction)
                stats['updated'] += 1
                
                target_calendar = "iCloud" if direction == 'google_to_icloud' else "Google Calendar"
                source_calendar = "Google Calendar" if direction == 'google_to_icloud' else "iCloud"
                old_time = self._format_event_time(rescheduled_event)
                new_time = self._format_event_time(source_event)
                
                print(f"{'[DRY RUN] ' if dry_run else ''}Rescheduling event: '{source_event['summary']}'")
                print(f"  └─ From: {source_calendar} → To: {target_calendar}")
                print(f"  └─ Old time: {old_time}")
                print(f"  └─ New time: {new_time}")
                print()
                continue
            
            # Third check: fuzzy match for similar events (same title, time, but maybe different description formatting)
            existing_event = self._find_similar_event(source_event, target_events)
            if existing_event:
                stats['skipped'] += 1
                print(f"{'[DRY RUN] ' if dry_run else ''}Skipping event: '{source_event['summary']}' (similar event already exists)")
                continue
            
            # No match found, create new event
            if not dry_run:
                self._create_event_in_target(source_event, direction)
            stats['created'] += 1
            
            # Enhanced logging with calendar destination and time details
            target_calendar = "iCloud" if direction == 'google_to_icloud' else "Google Calendar"
            source_calendar = "Google Calendar" if direction == 'google_to_icloud' else "iCloud"
            event_time = self._format_event_time(source_event)
            
            print(f"{'[DRY RUN] ' if dry_run else ''}Creating event: '{source_event['summary']}'")
            print(f"  └─ From: {source_calendar} → To: {target_calendar}")
            print(f"  └─ Time: {event_time}")
            if source_event.get('location'):
                print(f"  └─ Location: {source_event['location']}")
            print()  # Add blank line for readability
        
        return stats
    
    def _create_event_in_target(self, event: Dict[str, Any], direction: str) -> None:
        """Create an event in the target calendar."""
        try:
            if direction == 'google_to_icloud':
                # Convert Google event to iCloud format
                event_data = self._convert_to_icloud_format(event)
                self.icloud_client.create_event(event_data)
            elif direction == 'icloud_to_google':
                # Convert iCloud event to Google format
                event_data = self._convert_to_google_format(event)
                self.google_client.create_event(event_data)
        except Exception as e:
            print(f"Error creating event '{event['summary']}': {e}")
    
    def _update_event_in_target(self, source_event: Dict[str, Any], 
                                target_event: Dict[str, Any], direction: str) -> None:
        """Update an event in the target calendar."""
        try:
            if direction == 'google_to_icloud':
                # Update iCloud event
                event_data = self._convert_to_icloud_format(source_event)
                # For iCloud updates, we need the actual Event object
                # This is simplified - in practice, you'd need to find and update the actual event
                print(f"iCloud update not fully implemented for: {source_event['summary']}")
            elif direction == 'icloud_to_google':
                # Update Google event
                event_data = self._convert_to_google_format(source_event)
                event_id = target_event.get('id')
                if event_id:
                    self.google_client.update_event(event_id, event_data)
        except Exception as e:
            print(f"Error updating event '{source_event['summary']}': {e}")
    
    def _calculate_event_hash(self, event: Dict[str, Any]) -> str:
        """Calculate a hash for event content to detect duplicates."""
        # Create a string from key event properties for better duplicate detection
        # Only use summary and time - location can have too many formatting variations
        summary = self._normalize_text(event.get('summary', ''))
        start_time = str(event.get('start', ''))
        end_time = str(event.get('end', ''))
        
        # Include only title and time fields for more reliable duplicate detection
        hash_string = f"{summary}|{start_time}|{end_time}"
        return hashlib.md5(hash_string.encode()).hexdigest()
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison by removing formatting differences."""
        if not text:
            return ""
        
        # Remove common formatting differences
        normalized = text.strip()
        # Remove escaped characters common in calendar exports
        normalized = normalized.replace('\\,', ',')
        normalized = normalized.replace('\\;', ';')
        normalized = normalized.replace('\\n', '\n')
        normalized = normalized.replace('\\\\', '\\')
        # Normalize whitespace
        normalized = ' '.join(normalized.split())
        
        return normalized.lower()
    
    def _needs_update(self, source_event: Dict[str, Any], 
                      target_event: Dict[str, Any]) -> bool:
        """Check if an event needs to be updated."""
        # Compare key fields using normalized text for title/description
        # and exact comparison for times
        
        # Check title (normalized)
        source_title = self._normalize_text(source_event.get('summary', ''))
        target_title = self._normalize_text(target_event.get('summary', ''))
        if source_title != target_title:
            return True
        
        # Check description (normalized)
        source_desc = self._normalize_text(source_event.get('description', ''))
        target_desc = self._normalize_text(target_event.get('description', ''))
        if source_desc != target_desc:
            return True
        
        # Check times (exact comparison)
        if not self._times_match(source_event.get('start'), target_event.get('start')):
            return True
        if not self._times_match(source_event.get('end'), target_event.get('end')):
            return True
        
        # Skip location comparison as it's too prone to formatting differences
        # If title, description, and times match, consider it the same event
        
        return False
    
    def _convert_to_google_format(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Convert event to Google Calendar format."""
        google_event = {
            'summary': event.get('summary', ''),
            'description': event.get('description', ''),
            'location': event.get('location', ''),
        }
        
        # Handle datetime formatting
        if event.get('all_day'):
            google_event['start'] = {'date': event['start'].strftime('%Y-%m-%d')}
            google_event['end'] = {'date': event['end'].strftime('%Y-%m-%d')}
        else:
            # Preserve timezone information instead of converting to UTC
            start_dt = event['start']
            end_dt = event['end']
            
            # If the datetime is naive (no timezone), assume it's in local timezone
            if start_dt.tzinfo is None:
                local_tz = pytz.timezone(self.config.timezone)
                start_dt = local_tz.localize(start_dt)
                end_dt = local_tz.localize(end_dt)
            
            google_event['start'] = {
                'dateTime': start_dt.isoformat(), 
                'timeZone': str(start_dt.tzinfo)
            }
            google_event['end'] = {
                'dateTime': end_dt.isoformat(), 
                'timeZone': str(end_dt.tzinfo)
            }
        
        return google_event
    
    def _convert_to_icloud_format(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Convert event to iCloud Calendar format."""
        icloud_event = {
            'summary': event.get('summary', ''),
            'description': event.get('description', ''),
            'location': event.get('location', ''),
            'start': event.get('start'),
            'end': event.get('end'),
            'all_day': event.get('all_day', False)
        }
        
        return icloud_event
    
    def _format_event_time(self, event: Dict[str, Any]) -> str:
        """Format event time for display in logs."""
        start_time = event.get('start')
        end_time = event.get('end')
        
        if not start_time or not end_time:
            return "Time not available"
        
        if event.get('all_day'):
            # All-day event
            if start_time.date() == end_time.date():
                return f"{start_time.strftime('%A, %B %d, %Y')} (All day)"
            else:
                return f"{start_time.strftime('%B %d')} - {end_time.strftime('%B %d, %Y')} (All day)"
        else:
            # Timed event
            date_str = start_time.strftime('%A, %B %d, %Y')
            start_time_str = start_time.strftime('%I:%M %p').lstrip('0')
            end_time_str = end_time.strftime('%I:%M %p').lstrip('0')
            
            # Check if same date
            if start_time.date() == end_time.date():
                return f"{date_str} from {start_time_str} to {end_time_str}"
            else:
                # Multi-day event
                end_date_str = end_time.strftime('%A, %B %d, %Y')
                return f"{date_str} {start_time_str} → {end_date_str} {end_time_str}"
    
    def _find_rescheduled_event(self, source_event: Dict[str, Any], 
                               target_events: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find an event that matches description/summary but has different times (indicating a reschedule)."""
        source_summary = self._normalize_text(source_event.get('summary', ''))
        source_description = self._normalize_text(source_event.get('description', ''))
        source_start = source_event.get('start')
        source_end = source_event.get('end')
        
        # Need at least summary and time info
        if not source_summary or not source_start or not source_end:
            return None
        
        for target_event in target_events:
            target_summary = self._normalize_text(target_event.get('summary', ''))
            target_description = self._normalize_text(target_event.get('description', ''))
            target_start = target_event.get('start')
            target_end = target_event.get('end')
            
            # Check if summary matches
            summary_match = source_summary == target_summary
            description_match = source_description and target_description and source_description == target_description
            
            # Check if times are actually different (with improved matching)
            start_times_match = self._times_match(source_start, target_start)
            end_times_match = self._times_match(source_end, target_end)
            times_actually_different = not (start_times_match and end_times_match)
            
            # Only consider it a reschedule if:
            # 1. Summary matches exactly
            # 2. Description matches OR both are empty (ignore location for rescheduling)
            # 3. Times are genuinely different (not just formatting/timezone differences)
            # 4. The time difference is significant (more than 5 minutes)
            if summary_match and times_actually_different:
                # Additional check: ensure the time difference is meaningful
                if self._has_significant_time_difference(source_start, target_start, source_end, target_end):
                    if description_match or (not source_description and not target_description):
                        return target_event
        
        return None
    
    def _has_significant_time_difference(self, source_start, target_start, source_end, target_end) -> bool:
        """Check if there's a significant time difference between events (more than 5 minutes)."""
        try:
            if not all([source_start, target_start, source_end, target_end]):
                return False
            
            # Normalize timezone for comparison
            import pytz
            
            def normalize_time(dt):
                if dt.tzinfo is None:
                    # Assume local timezone
                    local_tz = pytz.timezone(self.config.timezone)
                    return local_tz.localize(dt)
                return dt
            
            source_start_norm = normalize_time(source_start)
            target_start_norm = normalize_time(target_start)
            source_end_norm = normalize_time(source_end)
            target_end_norm = normalize_time(target_end)
            
            # Convert to UTC for comparison
            utc = pytz.UTC
            source_start_utc = source_start_norm.astimezone(utc)
            target_start_utc = target_start_norm.astimezone(utc)
            source_end_utc = source_end_norm.astimezone(utc)
            target_end_utc = target_end_norm.astimezone(utc)
            
            # Check if either start or end time differs by more than 5 minutes
            start_diff = abs((source_start_utc - target_start_utc).total_seconds())
            end_diff = abs((source_end_utc - target_end_utc).total_seconds())
            
            # Consider it significant if either start or end differs by more than 5 minutes (300 seconds)
            return start_diff > 300 or end_diff > 300
            
        except Exception as e:
            # If we can't compare properly, be conservative and say no significant difference
            return False
    
    def _find_similar_event(self, source_event: Dict[str, Any], 
                           target_events: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find a similar event in target calendar to avoid creating duplicates."""
        source_summary = self._normalize_text(source_event.get('summary', ''))
        source_start = source_event.get('start')
        source_end = source_event.get('end')
        
        # If we don't have essential info, can't do fuzzy matching
        if not source_summary or not source_start or not source_end:
            return None
        
        for target_event in target_events:
            target_summary = self._normalize_text(target_event.get('summary', ''))
            target_start = target_event.get('start')
            target_end = target_event.get('end')
            
            # Check if summary and times match (normalized summary comparison)
            if (source_summary == target_summary and 
                self._times_match(source_start, target_start) and 
                self._times_match(source_end, target_end)):
                return target_event
        
        return None
    
    def _times_match(self, time1, time2, debug_info: str = "") -> bool:
        """Check if two datetime objects represent the same time (allowing for small differences)."""
        if not time1 or not time2:
            return False
        
        try:
            # Convert to same timezone if needed for comparison
            if hasattr(time1, 'replace') and hasattr(time2, 'replace'):
                # Normalize timezones for comparison
                if time1.tzinfo is not None and time2.tzinfo is not None:
                    # Both have timezone info - convert to UTC for comparison
                    import pytz
                    utc = pytz.UTC
                    t1_utc = time1.astimezone(utc).replace(microsecond=0)
                    t2_utc = time2.astimezone(utc).replace(microsecond=0)
                    diff = abs((t1_utc - t2_utc).total_seconds())
                elif time1.tzinfo is None and time2.tzinfo is None:
                    # Both are naive - compare directly
                    t1 = time1.replace(microsecond=0)
                    t2 = time2.replace(microsecond=0)
                    diff = abs((t1 - t2).total_seconds())
                else:
                    # Mixed timezone awareness - try to normalize
                    import pytz
                    local_tz = pytz.timezone(self.config.timezone)
                    
                    if time1.tzinfo is None:
                        # Assume time1 is in local timezone
                        time1 = local_tz.localize(time1)
                    if time2.tzinfo is None:
                        # Assume time2 is in local timezone
                        time2 = local_tz.localize(time2)
                    
                    utc = pytz.UTC
                    t1_utc = time1.astimezone(utc).replace(microsecond=0)
                    t2_utc = time2.astimezone(utc).replace(microsecond=0)
                    diff = abs((t1_utc - t2_utc).total_seconds())
                
                # Allow for small differences (up to 1 minute)
                return diff <= 60
                
        except Exception as e:
            # Fallback to string comparison
            return str(time1) == str(time2)
        
        return False
