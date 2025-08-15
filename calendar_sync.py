#!/usr/bin/env python3
"""
Calendar Sync Script
A tool to synchronize events between Google Calendar and iCloud Calendar
"""

import os
import json
import click
from datetime import datetime, timedelta
from dotenv import load_dotenv

from src.google_calendar import GoogleCalendarClient
from src.icloud_calendar import iCloudCalendarClient
from src.sync_engine import CalendarSyncEngine
from src.config import Config

# Load environment variables
load_dotenv()

@click.group()
def cli():
    """Calendar synchronization tool for Google Calendar and iCloud."""
    pass

@cli.command()
@click.option('--days', default=30, help='Number of days to sync (default: 30)')
@click.option('--dry-run', is_flag=True, help='Show what would be synced without making changes')
def sync(days, dry_run):
    """Sync calendars between Google and iCloud."""
    try:
        config = Config()
        
        # Initialize calendar clients
        google_client = GoogleCalendarClient(config)
        icloud_client = iCloudCalendarClient(config)
        
        # Initialize sync engine
        sync_engine = CalendarSyncEngine(google_client, icloud_client, config)
        
        # Perform synchronization
        start_date = datetime.now()
        end_date = start_date + timedelta(days=days)
        
        click.echo(f"Syncing calendars from {start_date.date()} to {end_date.date()}")
        if dry_run:
            click.echo("DRY RUN: No changes will be made")
        
        result = sync_engine.sync(start_date, end_date, dry_run=dry_run)
        
        click.echo(f"Sync completed successfully!")
        click.echo(f"Events processed: {result.get('events_processed', 0)}")
        click.echo(f"Events created: {result.get('events_created', 0)}")
        click.echo(f"Events updated: {result.get('events_updated', 0)}")
        click.echo(f"Events skipped: {result.get('events_skipped', 0)} (duplicates avoided)")
        
    except Exception as e:
        click.echo(f"Error during sync: {str(e)}", err=True)
        raise click.Abort()

@cli.command()
def setup():
    """Setup authentication for Google Calendar and iCloud."""
    click.echo("Setting up calendar sync authentication...")
    
    try:
        config = Config()
        
        # Setup Google Calendar
        click.echo("Setting up Google Calendar...")
        google_client = GoogleCalendarClient(config)
        google_client.authenticate()
        click.echo("✓ Google Calendar authentication completed")
        
        # Setup iCloud Calendar
        click.echo("Setting up iCloud Calendar...")
        icloud_client = iCloudCalendarClient(config)
        icloud_client.authenticate()
        click.echo("✓ iCloud Calendar authentication completed")
        
        click.echo("Authentication setup completed successfully!")
        
    except Exception as e:
        click.echo(f"Error during setup: {str(e)}", err=True)
        raise click.Abort()

@cli.command()
def status():
    """Check the status of calendar connections."""
    try:
        config = Config()
        
        # Check Google Calendar
        try:
            google_client = GoogleCalendarClient(config)
            google_calendars = google_client.list_calendars()
            click.echo(f"✓ Google Calendar: Connected ({len(google_calendars)} calendars)")
        except Exception as e:
            click.echo(f"✗ Google Calendar: Not connected ({str(e)})")
        
        # Check iCloud Calendar
        try:
            icloud_client = iCloudCalendarClient(config)
            icloud_calendars = icloud_client.list_calendars()
            click.echo(f"✓ iCloud Calendar: Connected ({len(icloud_calendars)} calendars)")
        except Exception as e:
            click.echo(f"✗ iCloud Calendar: Not connected ({str(e)})")
            
    except Exception as e:
        click.echo(f"Error checking status: {str(e)}", err=True)
        raise click.Abort()

@cli.command()
@click.option('--source', type=click.Choice(['google', 'icloud', 'auto']), 
              help='Set source of truth for bidirectional conflicts')
def configure(source):
    """Configure sync settings like source of truth for conflicts."""
    try:
        if source:
            # Update the .env file with the new source of truth
            import os
            from pathlib import Path
            
            env_file = Path('.env')
            if env_file.exists():
                # Read current content
                content = env_file.read_text()
                
                # Update or add SOURCE_OF_TRUTH line
                lines = content.split('\n')
                updated = False
                for i, line in enumerate(lines):
                    if line.startswith('SOURCE_OF_TRUTH='):
                        lines[i] = f'SOURCE_OF_TRUTH={source}'
                        updated = True
                        break
                
                if not updated:
                    lines.append(f'SOURCE_OF_TRUTH={source}')
                
                # Write back
                env_file.write_text('\n'.join(lines))
                click.echo(f"✓ Source of truth set to: {source}")
            else:
                click.echo("✗ .env file not found")
        else:
            # Show current configuration
            config = Config()
            click.echo("Current Configuration:")
            click.echo(f"  Sync Direction: {config.sync_direction}")
            click.echo(f"  Source of Truth: {config.source_of_truth}")
            click.echo(f"  Timezone: {config.timezone}")
            
            if config.sync_direction == 'both':
                click.echo()
                click.echo("💡 Tip: For bidirectional sync, set source of truth to resolve conflicts:")
                click.echo("   python calendar_sync.py configure --source google")
                click.echo("   python calendar_sync.py configure --source icloud")
                
    except Exception as e:
        click.echo(f"Error during configuration: {str(e)}", err=True)
        raise click.Abort()

if __name__ == '__main__':
    cli()
