"""
Gmail API Tools

Provides functions for interacting with Gmail API including:
- Draft management
- History tracking
- Label management
- Message handling
- Settings configuration
- Thread management
"""

import asyncio
import base64
import json
import logging
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import lru_cache
from typing import Any, Dict, List, Optional

from googleapiclient.discovery import build

from .credentials import CredentialsHandler
from .google_tool_base import GoogleToolBase

logger = logging.getLogger(__name__)

# Import from credentials handler using absolute path for direct testing
try:
    # When imported as a module
    from .credentials_handler import get_credentials
except ImportError:
    # When run directly
    import sys

    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Gmail-specific scopes
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://mail.google.com/",
    "https://www.googleapis.com/auth/gmail.settings.basic",
    "https://www.googleapis.com/auth/gmail.settings.sharing",
]


class GmailTools:
    """Gmail API tools implementation."""

    def __init__(self, credentials_handler: CredentialsHandler):
        """Initialize Gmail tools.

        Args:
            credentials_handler: Credentials handler instance
        """
        self.credentials_handler = credentials_handler
        self.service = None

    def _get_service(self):
        """Get the Gmail service."""
        if not self.service:
            creds = self.credentials_handler.get_credentials(GMAIL_SCOPES)
            if creds:
                self.service = build("gmail", "v1", credentials=creds)
        return self.service

    def _create_message(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """Create a message for an email.

        Args:
            to: Email recipient
            subject: The subject of the email message
            body: The text of the email message

        Returns:
            An object containing a base64url encoded email object
        """
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject

        raw = base64.urlsafe_b64encode(message.as_bytes())
        return {"raw": raw.decode()}

    # Draft Functions
    def drafts_get(self, draft_id: str) -> Dict[str, Any]:
        """Get a specific draft."""
        try:
            service = self._get_service()
            draft = service.users().drafts().get(userId="me", id=draft_id).execute()
            return {"success": True, "draft": draft}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def drafts_list(self, max_results: int = 10) -> Dict[str, Any]:
        """List email drafts."""
        try:
            service = self._get_service()
            drafts = service.users().drafts().list(userId="me", maxResults=max_results).execute()
            return {"success": True, "drafts": drafts.get("drafts", [])}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def drafts_create(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """Create a new draft."""
        try:
            service = self._get_service()
            message = self._create_message(to, subject, body)
            draft = (
                service.users().drafts().create(userId="me", body={"message": message}).execute()
            )
            return {"success": True, "draft_id": draft["id"]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def drafts_update(
        self, draft_id: str, to: str = None, subject: str = None, body: str = None
    ) -> Dict[str, Any]:
        """Update an existing draft."""
        try:
            service = self._get_service()
            message = self._create_message(to, subject, body or "")
            updated_draft = (
                service.users()
                .drafts()
                .update(userId="me", id=draft_id, body={"message": message})
                .execute()
            )
            return {"success": True, "draft": updated_draft}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def drafts_delete(self, draft_id: str) -> Dict[str, Any]:
        """Delete a draft."""
        try:
            service = self._get_service()
            service.users().drafts().delete(userId="me", id=draft_id).execute()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def drafts_send(self, draft_id: str) -> Dict[str, Any]:
        """Send an existing draft."""
        try:
            service = self._get_service()
            sent = service.users().drafts().send(userId="me", body={"id": draft_id}).execute()
            return {"success": True, "message_id": sent["id"]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Message Functions
    def messages_send(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """Send a new message."""
        try:
            service = self._get_service()
            message = self._create_message(to, subject, body)
            sent = service.users().messages().send(userId="me", body=message).execute()
            return {"success": True, "message_id": sent["id"]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def messages_get(self, message_id: str, format: str = "full") -> Dict[str, Any]:
        """Get a specific message."""
        try:
            service = self._get_service()
            message = (
                service.users().messages().get(userId="me", id=message_id, format=format).execute()
            )
            return {"success": True, "message": message}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def messages_list(self, max_results: int = 10, query: str = None) -> Dict[str, Any]:
        """List Gmail messages."""
        try:
            service = self._get_service()
            params = {"userId": "me", "maxResults": max_results, "labelIds": ["INBOX"]}
            if query:
                params["q"] = query

            results = service.users().messages().list(**params).execute()

            messages = []
            for msg in results.get("messages", []):
                message = (
                    service.users()
                    .messages()
                    .get(userId="me", id=msg["id"], format="metadata")
                    .execute()
                )
                headers = message["payload"]["headers"]
                subject = next(
                    (h["value"] for h in headers if h["name"] == "Subject"),
                    "No Subject",
                )
                sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown")
                messages.append({"id": msg["id"], "subject": subject, "from": sender})

            return {"success": True, "messages": messages}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Label Functions
    def labels_list(self) -> Dict[str, Any]:
        """List all labels."""
        try:
            service = self._get_service()
            labels = service.users().labels().list(userId="me").execute()
            return {"success": True, "labels": labels.get("labels", [])}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def labels_create(self, name: str, visibility: str = "labelShow") -> Dict[str, Any]:
        """Create a new label."""
        try:
            service = self._get_service()
            label = {
                "name": name,
                "labelListVisibility": visibility,
                "messageListVisibility": "show",
            }
            created = service.users().labels().create(userId="me", body=label).execute()
            return {"success": True, "label_id": created["id"]}
        except Exception as e:
            return {"success": False, "error": str(e)}


@lru_cache(maxsize=1)
def get_gmail_service():
    """Get and cache the Gmail service."""
    creds = get_credentials()
    return build("gmail", "v1", credentials=creds)


# Gmail History Functions
def gmail_history_list(max_results: int = 10) -> str:
    """List history of mailbox changes."""
    try:
        service = get_gmail_service()

        # First get a valid historyId from the profile
        profile = service.users().getProfile(userId="me").execute()
        start_history_id = profile.get("historyId")

        # Then use it to list history
        history = (
            service.users()
            .history()
            .list(userId="me", startHistoryId=start_history_id, maxResults=max_results)
            .execute()
        )

        return json.dumps(history.get("history", []), indent=2)
    except Exception as e:
        return f"Error listing history: {str(e)}"


# Gmail Labels Functions
def gmail_labels_delete(label_id: str) -> str:
    """Delete a label."""
    try:
        service = get_gmail_service()
        service.users().labels().delete(userId="me", id=label_id).execute()
        return "Label deleted successfully"
    except Exception as e:
        return f"Error deleting label: {str(e)}"


def gmail_labels_get(label_id: str) -> str:
    """Get a specific label."""
    try:
        service = get_gmail_service()
        label = service.users().labels().get(userId="me", id=label_id).execute()
        return json.dumps(label, indent=2)
    except Exception as e:
        return f"Error getting label: {str(e)}"


def gmail_labels_modify(label_id: str, name: str = None, visibility: str = None) -> str:
    """Modify an existing label."""
    try:
        service = get_gmail_service()
        body = {}
        if name:
            body["name"] = name
        if visibility:
            body["labelListVisibility"] = visibility

        result = service.users().labels().patch(userId="me", id=label_id, body=body).execute()
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error modifying label: {str(e)}"


# Gmail Messages Functions
def gmail_messages_trash(message_id: str) -> str:
    """Move a message to trash."""
    try:
        service = get_gmail_service()
        service.users().messages().trash(userId="me", id=message_id).execute()
        return "Message moved to trash successfully"
    except Exception as e:
        return f"Error moving message to trash: {str(e)}"


def gmail_messages_untrash(message_id: str) -> str:
    """Remove a message from trash."""
    try:
        service = get_gmail_service()
        service.users().messages().untrash(userId="me", id=message_id).execute()
        return "Message removed from trash successfully"
    except Exception as e:
        return f"Error removing message from trash: {str(e)}"


def gmail_messages_batch_delete(message_ids: List[str]) -> str:
    """Delete multiple messages."""
    try:
        service = get_gmail_service()
        service.users().messages().batchDelete(userId="me", body={"ids": message_ids}).execute()
        return "Messages deleted successfully"
    except Exception as e:
        return f"Error deleting messages: {str(e)}"


def gmail_messages_attachments_get(message_id: str, attachment_id: str) -> str:
    """Get a message attachment."""
    try:
        service = get_gmail_service()
        attachment = (
            service.users()
            .messages()
            .attachments()
            .get(userId="me", messageId=message_id, id=attachment_id)
            .execute()
        )
        return json.dumps(attachment, indent=2)
    except Exception as e:
        return f"Error getting attachment: {str(e)}"


def gmail_messages_create(to: str, subject: str, body: str, draft: bool = False) -> str:
    """Create a new message (as draft or sent)."""
    try:
        service = get_gmail_service()
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        if draft:
            result = (
                service.users()
                .drafts()
                .create(userId="me", body={"message": {"raw": raw}})
                .execute()
            )
        else:
            result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error creating message: {str(e)}"


def gmail_messages_delete(message_id: str) -> str:
    """Permanently delete a message."""
    try:
        service = get_gmail_service()
        service.users().messages().delete(userId="me", id=message_id).execute()
        return json.dumps(
            {
                "status": "success",
                "message": f"Message {message_id} deleted successfully",
            }
        )
    except Exception as e:
        return json.dumps(
            {
                "status": "error",
                "message": f"Error deleting message {message_id}: {str(e)}",
            }
        )


def gmail_messages_import(raw_email: str, labels: List[str] = None) -> str:
    """Import a raw message."""
    try:
        service = get_gmail_service()
        message = {"raw": base64.urlsafe_b64encode(raw_email.encode()).decode()}
        if labels:
            message["labelIds"] = labels

        result = service.users().messages().import_(userId="me", body=message).execute()
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error importing message: {str(e)}"


# Gmail Settings Functions
def gmail_settings_get_autoforwarding() -> str:
    """Get auto-forwarding settings."""
    try:
        service = get_gmail_service()
        result = service.users().settings().getAutoForwarding(userId="me").execute()
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error getting auto-forwarding settings: {str(e)}"


def gmail_settings_update_autoforwarding(enabled: bool, email: str = None) -> str:
    """Update auto-forwarding settings."""
    try:
        service = get_gmail_service()
        body = {"enabled": enabled, "emailAddress": email if enabled else None}
        result = service.users().settings().updateAutoForwarding(userId="me", body=body).execute()
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error updating auto-forwarding settings: {str(e)}"


def gmail_settings_get_vacation() -> str:
    """Get vacation responder settings."""
    try:
        service = get_gmail_service()
        result = service.users().settings().getVacation(userId="me").execute()
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error getting vacation settings: {str(e)}"


def gmail_settings_update_vacation(
    enabled: bool,
    response_subject: str = "",
    response_body: str = "",
    start_time: str = None,
    end_time: str = None,
) -> str:
    """Update vacation responder settings."""
    try:
        service = get_gmail_service()
        body = {
            "enableAutoReply": enabled,
            "responseSubject": response_subject,
            "responseBodyHtml": response_body,
        }
        if start_time:
            body["startTime"] = start_time
        if end_time:
            body["endTime"] = end_time

        result = service.users().settings().updateVacation(userId="me", body=body).execute()
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error updating vacation settings: {str(e)}"


# Gmail Settings Filters Functions
def gmail_settings_filters_create(
    from_email: str = None,
    to_email: str = None,
    subject: str = None,
    has_words: str = None,
    label_ids: List[str] = None,
) -> str:
    """Create a Gmail filter."""
    try:
        service = get_gmail_service()
        filter_criteria = {}
        if from_email:
            filter_criteria["from"] = from_email
        if to_email:
            filter_criteria["to"] = to_email
        if subject:
            filter_criteria["subject"] = subject
        if has_words:
            filter_criteria["query"] = has_words

        filter_action = {}
        if label_ids:
            filter_action["addLabelIds"] = label_ids

        body = {"criteria": filter_criteria, "action": filter_action}

        result = service.users().settings().filters().create(userId="me", body=body).execute()
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error creating filter: {str(e)}"


def gmail_settings_filters_delete(filter_id: str) -> str:
    """Delete a Gmail filter."""
    try:
        service = get_gmail_service()
        service.users().settings().filters().delete(userId="me", id=filter_id).execute()
        return "Filter deleted successfully"
    except Exception as e:
        return f"Error deleting filter: {str(e)}"


def gmail_settings_filters_get(filter_id: str) -> str:
    """Get a specific Gmail filter."""
    try:
        service = get_gmail_service()
        result = service.users().settings().filters().get(userId="me", id=filter_id).execute()
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error getting filter: {str(e)}"


def gmail_settings_filters_list() -> str:
    """List all Gmail filters."""
    try:
        service = get_gmail_service()
        results = service.users().settings().filters().list(userId="me").execute()
        return json.dumps(results.get("filter", []), indent=2)
    except Exception as e:
        return f"Error listing filters: {str(e)}"


# Gmail Threads Functions
def gmail_threads_delete(thread_id: str) -> str:
    """Delete a thread."""
    try:
        service = get_gmail_service()
        service.users().threads().delete(userId="me", id=thread_id).execute()
        return "Thread deleted successfully"
    except Exception as e:
        return f"Error deleting thread: {str(e)}"


def gmail_threads_get(thread_id: str) -> str:
    """Get a specific thread."""
    try:
        service = get_gmail_service()
        result = service.users().threads().get(userId="me", id=thread_id).execute()
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error getting thread: {str(e)}"


def gmail_threads_list(max_results: int = 10) -> str:
    """List email threads."""
    try:
        service = get_gmail_service()
        results = service.users().threads().list(userId="me", maxResults=max_results).execute()
        return json.dumps(results.get("threads", []), indent=2)
    except Exception as e:
        return f"Error listing threads: {str(e)}"


def gmail_threads_trash(thread_id: str) -> str:
    """Move a thread to trash."""
    try:
        service = get_gmail_service()
        service.users().threads().trash(userId="me", id=thread_id).execute()
        return "Thread moved to trash successfully"
    except Exception as e:
        return f"Error moving thread to trash: {str(e)}"


def gmail_threads_untrash(thread_id: str) -> str:
    """Remove a thread from trash."""
    try:
        service = get_gmail_service()
        service.users().threads().untrash(userId="me", id=thread_id).execute()
        return "Thread removed from trash successfully"
    except Exception as e:
        return f"Error removing thread from trash: {str(e)}"


def run_tests():
    """Run all Gmail function tests."""
    print("\nTesting Gmail Functions:")
    try:
        # Test Message Functions
        print("\n1. Testing Message Operations:")
        print("Listing messages...")
        messages = gmail_messages_list(max_results=5)
        print(f"Messages list result: {messages}")
        # ... rest of test code ...
    except Exception as e:
        print(f"\nTest failed: {str(e)}")
        import traceback

        print("\nFull traceback:")
        print(traceback.format_exc())


# Direct testing
if __name__ == "__main__":
    run_tests()


class GmailTool(GoogleToolBase):
    """Gmail tool implementation."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize Gmail tool.

        Args:
            config: Tool configuration
        """
        super().__init__(config, "gmail")
        self._gmail_tools = None

    async def initialize(self) -> bool:
        """Initialize Gmail connection."""
        if await super().initialize():
            try:
                self._gmail_tools = GmailTools(credentials_handler=self._creds_handler)
                self._gmail_tools._get_service()  # Test connection
                return True
            except Exception as e:
                logger.error(f"Failed to initialize Gmail: {e}")
                return False
        return False

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Gmail operations (stubbed for orchestrator testing)."""
        # --- STUB FOR TESTING: Comment out actual logic and simulate delay/dummy reply ---
        await asyncio.sleep(30)
        return {
            "success": True,
            "message": "[STUB] GmailTool.execute simulated 30s delay and dummy reply.",
            "params": params,
        }
        # --- END STUB ---
        # Original code is commented out below for reference:
        # try:
        #     action = params.get("action", "").lower()
        #     tools = self._gmail_tools
        #     if not tools or not tools.service:
        #         return {"success": False, "error": "Gmail service not initialized"}
        #     if action == "send":
        #         return tools.messages_send(
        #             to=params["to"],
        #             subject=params["subject"],
        #             body=params["body"]
        #         )
        #     elif action == "read":
        #         return tools.messages_get(message_id=params["message_id"])
        #     elif action == "search":
        #         return tools.messages_list(
        #             max_results=params.get("max_results", 10),
        #             query=params.get("query")
        #         )
        #     elif action == "list_drafts":
        #         return tools.drafts_list(max_results=params.get("max_results", 10))
        #     elif action == "create_draft":
        #         return tools.drafts_create(
        #             to=params["to"],
        #             subject=params["subject"],
        #             body=params["body"]
        #         )
        #     elif action == "send_draft":
        #         return tools.drafts_send(draft_id=params["draft_id"])
        #     elif action == "delete_draft":
        #         return tools.drafts_delete(draft_id=params["draft_id"])
        #     elif action == "list_labels":
        #         return tools.labels_list()
        #     elif action == "create_label":
        #         return tools.labels_create(
        #             name=params["name"],
        #             visibility=params.get("visibility", "labelShow")
        #         )
        #     else:
        #         return {"success": False, "error": f"Unsupported Gmail action: {action}"}
        # except Exception as e:
        #     logger.error(f"Gmail operation failed: {e}")
        #     return {"success": False, "error": str(e)}
