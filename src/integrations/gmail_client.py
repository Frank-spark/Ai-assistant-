"""Gmail integration client for Reflex Executive Assistant."""

import logging
import base64
import email
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..config import get_settings
from ..storage.models import EmailMessage, EmailDraft

logger = logging.getLogger(__name__)


@dataclass
class GmailMessage:
    """Gmail message structure."""
    message_id: str
    thread_id: str
    subject: str
    sender: str
    recipients: List[str]
    body: str
    timestamp: datetime
    labels: List[str]
    attachments: List[Dict[str, Any]]


@dataclass
class EmailDraftRequest:
    """Email draft request structure."""
    to: List[str]
    subject: str
    body: str
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None
    reply_to_message_id: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None


class GmailClient:
    """Gmail API client for email operations."""
    
    # Gmail API scopes
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.modify',
        'https://www.googleapis.com/auth/gmail.compose'
    ]
    
    def __init__(self):
        """Initialize the Gmail client."""
        self.settings = get_settings()
        self.service = None
        self.credentials = None
        
        # Initialize the client
        self._init_client()
    
    def _init_client(self):
        """Initialize the Gmail API client."""
        try:
            # Try to use service account credentials first
            if self.settings.google_service_account_json_base64:
                self._init_service_account()
            else:
                # Fall back to OAuth flow
                self._init_oauth()
            
            # Build the Gmail service
            self.service = build('gmail', 'v1', credentials=self.credentials)
            logger.info("Gmail client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gmail client: {e}")
            raise
    
    def _init_service_account(self):
        """Initialize using service account credentials."""
        try:
            # Decode base64 service account JSON
            service_account_json = base64.b64decode(
                self.settings.google_service_account_json_base64
            ).decode('utf-8')
            
            # Create credentials from service account
            self.credentials = Credentials.from_service_account_info(
                eval(service_account_json),
                scopes=self.SCOPES
            )
            
            # Impersonate the target user if needed
            if hasattr(self.settings, 'google_target_user'):
                self.credentials = self.credentials.with_subject(
                    self.settings.google_target_user
                )
            
            logger.info("Gmail client initialized with service account")
            
        except Exception as e:
            logger.error(f"Failed to initialize service account: {e}")
            raise
    
    def _init_oauth(self):
        """Initialize using OAuth flow."""
        try:
            # Load existing credentials
            creds = None
            if hasattr(self.settings, 'google_token_file'):
                creds = Credentials.from_authorized_user_file(
                    self.settings.google_token_file, self.SCOPES
                )
            
            # If no valid credentials available, let the user log in
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_config(
                        {
                            "installed": {
                                "client_id": self.settings.google_client_id,
                                "client_secret": self.settings.google_client_secret,
                                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                                "token_uri": "https://oauth2.googleapis.com/token",
                                "redirect_uris": [self.settings.google_redirect_uri]
                            }
                        },
                        self.SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                
                # Save the credentials for the next run
                if hasattr(self.settings, 'google_token_file'):
                    with open(self.settings.google_token_file, 'w') as token:
                        token.write(creds.to_json())
            
            self.credentials = creds
            logger.info("Gmail client initialized with OAuth")
            
        except Exception as e:
            logger.error(f"Failed to initialize OAuth: {e}")
            raise
    
    async def get_messages(self, query: str = "", max_results: int = 10) -> List[GmailMessage]:
        """Get Gmail messages based on query."""
        try:
            # Build the query
            if not query:
                query = "in:inbox"
            
            # Get message IDs
            response = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = []
            for msg in response.get('messages', []):
                message = await self._get_message_details(msg['id'])
                if message:
                    messages.append(message)
            
            logger.info(f"Retrieved {len(messages)} messages for query: {query}")
            return messages
            
        except HttpError as e:
            logger.error(f"Gmail API error getting messages: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting Gmail messages: {e}")
            return []
    
    async def _get_message_details(self, message_id: str) -> Optional[GmailMessage]:
        """Get detailed message information."""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            # Extract headers
            headers = message['payload'].get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
            to = next((h['value'] for h in headers if h['name'] == 'To'), '')
            
            # Parse recipients
            recipients = [r.strip() for r in to.split(',') if r.strip()]
            
            # Extract body
            body = self._extract_message_body(message['payload'])
            
            # Parse timestamp
            timestamp = datetime.fromtimestamp(
                int(message['internalDate']) / 1000
            )
            
            # Get labels
            labels = message.get('labelIds', [])
            
            # Get attachments info
            attachments = self._extract_attachments_info(message['payload'])
            
            return GmailMessage(
                message_id=message_id,
                thread_id=message['threadId'],
                subject=subject,
                sender=sender,
                recipients=recipients,
                body=body,
                timestamp=timestamp,
                labels=labels,
                attachments=attachments
            )
            
        except Exception as e:
            logger.error(f"Error getting message details for {message_id}: {e}")
            return None
    
    def _extract_message_body(self, payload: Dict[str, Any]) -> str:
        """Extract message body from payload."""
        body = ""
        
        if 'body' in payload and payload['body'].get('data'):
            # Simple text message
            body = base64.urlsafe_b64decode(
                payload['body']['data']
            ).decode('utf-8')
        elif 'parts' in payload:
            # Multipart message
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if part['body'].get('data'):
                        body = base64.urlsafe_b64decode(
                            part['body']['data']
                        ).decode('utf-8')
                        break
        
        return body
    
    def _extract_attachments_info(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract attachment information from payload."""
        attachments = []
        
        def extract_from_parts(parts):
            for part in parts:
                if part.get('filename'):
                    attachments.append({
                        'id': part['body'].get('attachmentId'),
                        'filename': part['filename'],
                        'mime_type': part['mimeType'],
                        'size': part['body'].get('size', 0)
                    })
                if 'parts' in part:
                    extract_from_parts(part['parts'])
        
        if 'parts' in payload:
            extract_from_parts(payload['parts'])
        
        return attachments
    
    async def create_draft(self, draft_request: EmailDraftRequest) -> Optional[str]:
        """Create an email draft."""
        try:
            # Build the email message
            message = self._build_email_message(draft_request)
            
            # Create the draft
            draft = self.service.users().drafts().create(
                userId='me',
                body={'message': message}
            ).execute()
            
            draft_id = draft['id']
            logger.info(f"Created email draft: {draft_id}")
            
            return draft_id
            
        except HttpError as e:
            logger.error(f"Gmail API error creating draft: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating email draft: {e}")
            return None
    
    def _build_email_message(self, draft_request: EmailDraftRequest) -> Dict[str, Any]:
        """Build Gmail API message structure."""
        # Build headers
        headers = []
        headers.append(f"To: {', '.join(draft_request.to)}")
        
        if draft_request.cc:
            headers.append(f"Cc: {', '.join(draft_request.cc)}")
        
        if draft_request.bcc:
            headers.append(f"Bcc: {', '.join(draft_request.bcc)}")
        
        headers.append(f"Subject: {draft_request.subject}")
        headers.append("Content-Type: text/plain; charset=utf-8")
        
        # Build message
        message_text = '\r\n'.join(headers) + '\r\n\r\n' + draft_request.body
        
        # Encode message
        encoded_message = base64.urlsafe_b64encode(
            message_text.encode('utf-8')
        ).decode('utf-8')
        
        message = {
            'raw': encoded_message
        }
        
        # Add reply-to if specified
        if draft_request.reply_to_message_id:
            message['threadId'] = draft_request.reply_to_message_id
        
        return message
    
    async def send_draft(self, draft_id: str) -> bool:
        """Send an email draft."""
        try:
            self.service.users().drafts().send(
                userId='me',
                body={'id': draft_id}
            ).execute()
            
            logger.info(f"Sent email draft: {draft_id}")
            return True
            
        except HttpError as e:
            logger.error(f"Gmail API error sending draft: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending email draft: {e}")
            return False
    
    async def send_message(self, draft_request: EmailDraftRequest) -> bool:
        """Send an email message directly."""
        try:
            # Build and send the message
            message = self._build_email_message(draft_request)
            
            self.service.users().messages().send(
                userId='me',
                body=message
            ).execute()
            
            logger.info("Email message sent successfully")
            return True
            
        except HttpError as e:
            logger.error(f"Gmail API error sending message: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending email message: {e}")
            return False
    
    async def get_thread(self, thread_id: str) -> List[GmailMessage]:
        """Get all messages in a thread."""
        try:
            thread = self.service.users().threads().get(
                userId='me',
                id=thread_id
            ).execute()
            
            messages = []
            for msg in thread['messages']:
                message = await self._get_message_details(msg['id'])
                if message:
                    messages.append(message)
            
            # Sort by timestamp
            messages.sort(key=lambda x: x.timestamp)
            
            logger.info(f"Retrieved {len(messages)} messages from thread: {thread_id}")
            return messages
            
        except HttpError as e:
            logger.error(f"Gmail API error getting thread: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting thread: {e}")
            return []
    
    async def add_labels(self, message_id: str, label_ids: List[str]) -> bool:
        """Add labels to a message."""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': label_ids}
            ).execute()
            
            logger.info(f"Added labels {label_ids} to message: {message_id}")
            return True
            
        except HttpError as e:
            logger.error(f"Gmail API error adding labels: {e}")
            return False
        except Exception as e:
            logger.error(f"Error adding labels: {e}")
            return False
    
    async def remove_labels(self, message_id: str, label_ids: List[str]) -> bool:
        """Remove labels from a message."""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': label_ids}
            ).execute()
            
            logger.info(f"Removed labels {label_ids} from message: {message_id}")
            return True
            
        except HttpError as e:
            logger.error(f"Gmail API error removing labels: {e}")
            return False
        except Exception as e:
            logger.error(f"Error removing labels: {e}")
            return False
    
    async def get_labels(self) -> List[Dict[str, Any]]:
        """Get available Gmail labels."""
        try:
            labels = self.service.users().labels().list(
                userId='me'
            ).execute()
            
            return labels.get('labels', [])
            
        except HttpError as e:
            logger.error(f"Gmail API error getting labels: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting labels: {e}")
            return []
    
    async def search_messages(self, query: str, max_results: int = 20) -> List[GmailMessage]:
        """Search for messages using Gmail search syntax."""
        return await self.get_messages(query, max_results)
    
    async def get_recent_messages(self, hours: int = 24) -> List[GmailMessage]:
        """Get recent messages from the last N hours."""
        query = f"after:{(datetime.now() - timedelta(hours=hours)).strftime('%Y/%m/%d')}"
        return await self.get_messages(query, max_results=50)
    
    async def get_unread_messages(self, max_results: int = 20) -> List[GmailMessage]:
        """Get unread messages."""
        return await self.get_messages("is:unread", max_results)
    
    async def mark_as_read(self, message_id: str) -> bool:
        """Mark a message as read."""
        return await self.remove_labels(message_id, ['UNREAD'])
    
    async def mark_as_unread(self, message_id: str) -> bool:
        """Mark a message as unread."""
        return await self.add_labels(message_id, ['UNREAD'])
    
    async def archive_message(self, message_id: str) -> bool:
        """Archive a message (remove from inbox)."""
        return await self.remove_labels(message_id, ['INBOX'])
    
    async def move_to_inbox(self, message_id: str) -> bool:
        """Move a message to inbox."""
        return await self.add_labels(message_id, ['INBOX'])


# Global Gmail client instance
_gmail_client: Optional[GmailClient] = None


def get_gmail_client() -> GmailClient:
    """Get the global Gmail client instance."""
    global _gmail_client
    
    if _gmail_client is None:
        _gmail_client = GmailClient()
    
    return _gmail_client


async def send_email_notification(
    to: List[str],
    subject: str,
    body: str,
    cc: Optional[List[str]] = None
) -> bool:
    """Send an email notification."""
    client = get_gmail_client()
    
    draft_request = EmailDraftRequest(
        to=to,
        subject=subject,
        body=body,
        cc=cc
    )
    
    return await client.send_message(draft_request) 