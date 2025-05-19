# Personal Assistant Sub-Graph

This sub-graph implements a collection of tools for personal assistant functionality, enabling interaction with various services and APIs.

## Features

- Gmail integration for email management
- (Future) Slack integration for messaging
- (Future) Discord integration for communication
- (Future) Calendar integration for scheduling

## Setup

### Gmail Integration

To use Gmail integration:

1. Enable the Gmail API in Google Cloud Console:
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project or select an existing one
   - Enable the Gmail API
   - Create OAuth 2.0 credentials (Desktop application type)
   - Download the credentials file as `credentials.json`

2. Configure environment variables:
   ```bash
   # Enable Gmail integration
   GMAIL_ENABLED=true

   # Path to your credentials file
   GMAIL_CREDENTIALS_PATH=/path/to/your/credentials.json

   # Optional: Path for token storage (defaults to token.pickle)
   GMAIL_TOKEN_PATH=/path/to/token.pickle

   # Optional: Gmail user ID (defaults to 'me')
   GMAIL_USER_ID=your.email@gmail.com
   ```

3. First run will prompt for OAuth authentication:
   - A browser window will open
   - Sign in with your Google account
   - Grant the requested permissions
   - The token will be saved for future use

### Available Gmail Operations

The personal assistant can:
- Send emails
- Read emails
- Search emails

Example tasks:
```
"Send an email to john@example.com about the meeting tomorrow"
"Check my recent emails"
"Read emails about project updates"
```

## Error Handling

Common errors and solutions:

1. "Gmail tool not configured":
   - Make sure `GMAIL_ENABLED` is set to `true`
   - Check that `GMAIL_CREDENTIALS_PATH` points to a valid credentials file

2. "Failed to initialize Gmail":
   - Check that your credentials file is valid
   - Ensure you have granted the necessary permissions
   - Try deleting `token.pickle` and re-authenticating

3. "Unsupported Gmail action":
   - Check that you're using one of the supported operations (send, read/check)
   - Make sure your request is clear about what you want to do

## Usage

### Gmail Tool

The Gmail tool provides the following actions:

- `send_email`: Send emails with optional attachments
- `read_email`: Read specific emails by ID
- `search_emails`: Search emails using Gmail query syntax
- `list_emails`: List emails from specific folders/labels

Example usage:
```python
from tools.gmail import GmailTool

gmail = GmailTool()
await gmail.initialize()

# Send an email
await gmail.execute({
    "action": "send_email",
    "to": "recipient@example.com",
    "subject": "Test Email",
    "body": "Hello from the Personal Assistant!"
})

# Clean up
await gmail.cleanup()
```

## Development

### Adding New Tools

1. Create a new tool class in `tools/` inheriting from `PersonalAssistantTool`
2. Implement required methods:
   - `initialize()`: Setup connections and auth
   - `cleanup()`: Clean up resources
   - `execute(params)`: Handle tool actions

### Testing

Run tests using pytest:
```bash
pytest tests/
```

## Contributing

1. Follow Python best practices and PEP 8
2. Add tests for new functionality
3. Update documentation for new features
4. Keep dependencies up to date

## License

MIT License - See LICENSE file for details
