# Calendar Sync

A Python script for synchronizing events between Google Calendar and iCloud Calendar.

## Features

- **Bidirectional Sync**: Sync events from Google to iCloud, iCloud to Google, or both directions
- **OAuth Authentication**: Secure authentication with Google Calendar API
- **CalDAV Support**: Connect to iCloud calendars using the CalDAV protocol
- **Flexible Configuration**: Configure sync direction, frequency, and calendar selection
- **Dry Run Mode**: Preview changes before applying them
- **Command Line Interface**: Easy-to-use CLI for managing synchronization

## Prerequisites

1. **Google Calendar API Setup**:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Google Calendar API
   - Create OAuth 2.0 credentials (Desktop application)
   - Download the credentials file and save it as `credentials.json` in the project root

2. **iCloud Setup**:
   - Enable two-factor authentication on your Apple ID
   - Generate an app-specific password for this application
   - Note: You'll need your iCloud username and app-specific password

## Installation

1. Clone or download this repository
2. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy the environment template and configure your settings:
   ```bash
   copy .env.example .env
   ```

4. Edit the `.env` file with your credentials:
   ```
   ICLOUD_USERNAME=your_icloud_username@icloud.com
   ICLOUD_PASSWORD=your_app_specific_password
   ```

## Usage

### First Time Setup

Run the setup command to authenticate with both calendar services:

```bash
python calendar_sync.py setup
```

This will:
- Guide you through Google OAuth authentication
- Test your iCloud credentials
- Verify connectivity to both services

### Check Connection Status

```bash
python calendar_sync.py status
```

### Sync Calendars

Basic sync (30 days forward):
```bash
python calendar_sync.py sync
```

Sync specific number of days:
```bash
python calendar_sync.py sync --days 60
```

Preview changes without applying (dry run):
```bash
python calendar_sync.py sync --dry-run
```

## Configuration

### Environment Variables

- `GOOGLE_CREDENTIALS_FILE`: Path to Google OAuth credentials file (default: `credentials.json`)
- `GOOGLE_TOKEN_FILE`: Path to store Google access token (default: `token.json`)
- `GOOGLE_CALENDAR_ID`: Google Calendar ID to sync (default: `primary`)
- `ICLOUD_USERNAME`: Your iCloud username/email
- `ICLOUD_PASSWORD`: Your iCloud app-specific password
- `ICLOUD_SERVER`: iCloud CalDAV server URL (default: `https://caldav.icloud.com`)
- `SYNC_DIRECTION`: Direction of sync - `both`, `google_to_icloud`, or `icloud_to_google`
- `SYNC_FREQUENCY`: Sync frequency in minutes (for future scheduled sync feature)

### Sync Directions

- **`both`**: Bidirectional sync (events from both calendars will be synchronized)
- **`google_to_icloud`**: One-way sync from Google Calendar to iCloud
- **`icloud_to_google`**: One-way sync from iCloud to Google Calendar

## Security Notes

- Never commit your `.env` file or `credentials.json` to version control
- Store your iCloud app-specific password securely
- The Google token file contains sensitive authentication data
- Consider using a dedicated iCloud account for testing

## Troubleshooting

### Google Calendar Issues
- Ensure your `credentials.json` file is valid and in the project root
- Check that the Google Calendar API is enabled in your Google Cloud project
- Verify your OAuth consent screen is properly configured

### iCloud Calendar Issues
- Confirm you're using an app-specific password, not your regular iCloud password
- Check that two-factor authentication is enabled on your Apple ID
- Verify your iCloud username is correct (usually your Apple ID email)

### Sync Issues
- Run with `--dry-run` first to preview changes
- Check the `status` command to verify both services are connected
- Review the console output for specific error messages

## Limitations

- The iCloud calendar implementation uses CalDAV and may have some limitations compared to native APIs
- Event updates in iCloud are simplified in this implementation
- Some advanced calendar features (recurrence, attendees, etc.) may not be fully supported
- Rate limiting from calendar services may affect sync performance

## Future Enhancements

- Scheduled automatic synchronization
- Support for multiple calendars
- Advanced conflict resolution
- Support for recurring events
- Calendar-specific sync rules
- Web interface for configuration

## Contributing

This is a basic implementation that can be extended. Key areas for improvement:
- Enhanced iCalendar parsing for iCloud events
- Better error handling and retry logic
- Support for more calendar providers
- Improved conflict resolution strategies

## License

This project is provided as-is for educational and personal use.
