<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->
- [x] Verify that the copilot-instructions.md file in the .github directory is created.

- [x] Clarify Project Requirements - Python calendar sync project with Google Calendar API and iCloud CalDAV integration

- [x] Scaffold the Project - Created Python project structure with calendar sync modules, CLI interface, and configuration

- [x] Customize the Project - Implemented calendar sync functionality with Google Calendar API and iCloud CalDAV integration

- [x] Install Required Extensions - No extensions required for Python project

- [x] Compile the Project - Python project ready (requires Python installation and pip install -r requirements.txt)

- [x] Create and Run Task - Python CLI project doesn't require VS Code tasks

- [x] Launch the Project - Ready to run with python calendar_sync.py (after Python installation and dependency setup)

- [x] Ensure Documentation is Complete - README.md and copilot-instructions.md are complete with project information

## Calendar Sync Project

This workspace contains a Python-based calendar synchronization tool that syncs events between Google Calendar and iCloud Calendar.

### Key Features:
- Bidirectional synchronization between Google Calendar and iCloud
- OAuth authentication for Google Calendar API
- CalDAV protocol support for iCloud calendar access
- Command-line interface with sync, setup, and status commands
- Configurable sync direction and dry-run mode
- Comprehensive error handling and logging

### Project Structure:
- `calendar_sync.py` - Main CLI application
- `src/` - Core modules for calendar clients and sync engine
- `requirements.txt` - Python dependencies
- `.env.example` - Environment configuration template
- `README.md` - Complete setup and usage instructions

### Next Steps:
1. Install Python 3.7+ on your system
2. Run `pip install -r requirements.txt` to install dependencies
3. Copy `.env.example` to `.env` and configure your credentials
4. Set up Google Calendar API credentials (see README.md)
5. Run `python calendar_sync.py setup` to authenticate
6. Use `python calendar_sync.py sync` to synchronize calendars

Work through each checklist item systematically.
Keep communication concise and focused.
Follow development best practices.
