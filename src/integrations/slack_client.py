"""Slack integration client for Reflex Executive Assistant."""

import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from ..config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class SlackMessage:
    """Slack message structure."""
    message_id: str
    channel_id: str
    user_id: str
    text: str
    timestamp: str
    thread_ts: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    blocks: Optional[List[Dict[str, Any]]] = None


@dataclass
class SlackChannel:
    """Slack channel structure."""
    channel_id: str
    name: str
    is_private: bool
    is_archived: bool
    member_count: int
    topic: Optional[str] = None
    purpose: Optional[str] = None


@dataclass
class SlackUser:
    """Slack user structure."""
    user_id: str
    username: str
    real_name: Optional[str] = None
    email: Optional[str] = None
    is_bot: bool = False
    is_admin: bool = False


class SlackClient:
    """Slack API client for messaging and operations."""
    
    def __init__(self):
        """Initialize the Slack client."""
        self.settings = get_settings()
        self.client = None
        self.async_client = None
        
        # Initialize the client
        self._init_client()
    
    def _init_client(self):
        """Initialize the Slack API client."""
        try:
            # Initialize both sync and async clients
            self.client = WebClient(token=self.settings.slack_bot_token)
            self.async_client = AsyncWebClient(token=self.settings.slack_bot_token)
            
            # Test the connection
            auth_test = self.client.auth_test()
            bot_user_id = auth_test["user_id"]
            team_name = auth_test["team"]
            
            logger.info(f"Slack client initialized successfully for team: {team_name}, bot user: {bot_user_id}")
            
        except SlackApiError as e:
            logger.error(f"Slack API error initializing client: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Slack client: {e}")
            raise
    
    async def send_message(
        self,
        channel: str,
        text: str,
        thread_ts: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        blocks: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[str]:
        """Send a message to a Slack channel."""
        try:
            response = await self.async_client.chat_postMessage(
                channel=channel,
                text=text,
                thread_ts=thread_ts,
                attachments=attachments,
                blocks=blocks
            )
            
            message_ts = response["ts"]
            logger.info(f"Message sent to channel {channel}: {message_ts}")
            
            return message_ts
            
        except SlackApiError as e:
            logger.error(f"Slack API error sending message: {e}")
            return None
        except Exception as e:
            logger.error(f"Error sending Slack message: {e}")
            return None
    
    async def send_dm(self, user_id: str, text: str, **kwargs) -> Optional[str]:
        """Send a direct message to a user."""
        try:
            # Open DM channel
            response = await self.async_client.conversations_open(users=[user_id])
            channel_id = response["channel"]["id"]
            
            # Send message
            return await self.send_message(channel_id, text, **kwargs)
            
        except SlackApiError as e:
            logger.error(f"Slack API error sending DM: {e}")
            return None
        except Exception as e:
            logger.error(f"Error sending Slack DM: {e}")
            return None
    
    async def reply_to_message(
        self,
        channel: str,
        thread_ts: str,
        text: str,
        **kwargs
    ) -> Optional[str]:
        """Reply to a message in a thread."""
        return await self.send_message(channel, text, thread_ts=thread_ts, **kwargs)
    
    async def send_interactive_message(
        self,
        channel: str,
        text: str,
        blocks: List[Dict[str, Any]],
        **kwargs
    ) -> Optional[str]:
        """Send an interactive message with blocks."""
        return await self.send_message(
            channel=channel,
            text=text,
            blocks=blocks,
            **kwargs
        )
    
    async def send_approval_message(
        self,
        channel: str,
        title: str,
        description: str,
        actions: List[Dict[str, Any]],
        **kwargs
    ) -> Optional[str]:
        """Send an approval message with action buttons."""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": title
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": description
                }
            },
            {
                "type": "actions",
                "elements": actions
            }
        ]
        
        return await self.send_interactive_message(channel, text=title, blocks=blocks, **kwargs)
    
    async def get_channel_info(self, channel_id: str) -> Optional[SlackChannel]:
        """Get information about a Slack channel."""
        try:
            response = await self.async_client.conversations_info(channel=channel_id)
            channel_info = response["channel"]
            
            return SlackChannel(
                channel_id=channel_info["id"],
                name=channel_info["name"],
                is_private=channel_info.get("is_private", False),
                is_archived=channel_info.get("is_archived", False),
                member_count=channel_info.get("num_members", 0),
                topic=channel_info.get("topic", {}).get("value"),
                purpose=channel_info.get("purpose", {}).get("value")
            )
            
        except SlackApiError as e:
            logger.error(f"Slack API error getting channel info: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting channel info: {e}")
            return None
    
    async def get_user_info(self, user_id: str) -> Optional[SlackUser]:
        """Get information about a Slack user."""
        try:
            response = await self.async_client.users_info(user=user_id)
            user_info = response["user"]
            
            return SlackUser(
                user_id=user_info["id"],
                username=user_info["name"],
                real_name=user_info.get("real_name"),
                email=user_info.get("profile", {}).get("email"),
                is_bot=user_info.get("is_bot", False),
                is_admin=user_info.get("is_admin", False)
            )
            
        except SlackApiError as e:
            logger.error(f"Slack API error getting user info: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return None
    
    async def get_channel_members(self, channel_id: str) -> List[str]:
        """Get list of member IDs in a channel."""
        try:
            response = await self.async_client.conversations_members(channel=channel_id)
            return response["members"]
            
        except SlackApiError as e:
            logger.error(f"Slack API error getting channel members: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting channel members: {e}")
            return []
    
    async def get_channel_history(
        self,
        channel_id: str,
        limit: int = 100,
        oldest: Optional[str] = None,
        latest: Optional[str] = None
    ) -> List[SlackMessage]:
        """Get message history from a channel."""
        try:
            response = await self.async_client.conversations_history(
                channel=channel_id,
                limit=limit,
                oldest=oldest,
                latest=latest
            )
            
            messages = []
            for msg in response["messages"]:
                message = SlackMessage(
                    message_id=msg["ts"],
                    channel_id=channel_id,
                    user_id=msg.get("user", "Unknown"),
                    text=msg.get("text", ""),
                    timestamp=msg["ts"],
                    thread_ts=msg.get("thread_ts"),
                    attachments=msg.get("attachments"),
                    blocks=msg.get("blocks")
                )
                messages.append(message)
            
            return messages
            
        except SlackApiError as e:
            logger.error(f"Slack API error getting channel history: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting channel history: {e}")
            return []
    
    async def add_reaction(
        self,
        channel: str,
        timestamp: str,
        name: str
    ) -> bool:
        """Add a reaction to a message."""
        try:
            await self.async_client.reactions_add(
                channel=channel,
                timestamp=timestamp,
                name=name
            )
            
            logger.info(f"Added reaction {name} to message {timestamp} in channel {channel}")
            return True
            
        except SlackApiError as e:
            logger.error(f"Slack API error adding reaction: {e}")
            return False
        except Exception as e:
            logger.error(f"Error adding reaction: {e}")
            return False
    
    async def remove_reaction(
        self,
        channel: str,
        timestamp: str,
        name: str
    ) -> bool:
        """Remove a reaction from a message."""
        try:
            await self.async_client.reactions_remove(
                channel=channel,
                timestamp=timestamp,
                name=name
            )
            
            logger.info(f"Removed reaction {name} from message {timestamp} in channel {channel}")
            return True
            
        except SlackApiError as e:
            logger.error(f"Slack API error removing reaction: {e}")
            return False
        except Exception as e:
            logger.error(f"Error removing reaction: {e}")
            return False
    
    async def update_message(
        self,
        channel: str,
        timestamp: str,
        text: str,
        **kwargs
    ) -> bool:
        """Update an existing message."""
        try:
            await self.async_client.chat_update(
                channel=channel,
                ts=timestamp,
                text=text,
                **kwargs
            )
            
            logger.info(f"Updated message {timestamp} in channel {channel}")
            return True
            
        except SlackApiError as e:
            logger.error(f"Slack API error updating message: {e}")
            return False
        except Exception as e:
            logger.error(f"Error updating message: {e}")
            return False
    
    async def delete_message(self, channel: str, timestamp: str) -> bool:
        """Delete a message."""
        try:
            await self.async_client.chat_delete(
                channel=channel,
                ts=timestamp
            )
            
            logger.info(f"Deleted message {timestamp} in channel {channel}")
            return True
            
        except SlackApiError as e:
            logger.error(f"Slack API error deleting message: {e}")
            return False
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
            return False
    
    async def invite_to_channel(
        self,
        channel_id: str,
        user_ids: List[str]
    ) -> bool:
        """Invite users to a channel."""
        try:
            await self.async_client.conversations_invite(
                channel=channel_id,
                users=",".join(user_ids)
            )
            
            logger.info(f"Invited users {user_ids} to channel {channel_id}")
            return True
            
        except SlackApiError as e:
            logger.error(f"Slack API error inviting users: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inviting users: {e}")
            return False
    
    async def create_channel(self, name: str, is_private: bool = False) -> Optional[str]:
        """Create a new Slack channel."""
        try:
            response = await self.async_client.conversations_create(
                name=name,
                is_private=is_private
            )
            
            channel_id = response["channel"]["id"]
            logger.info(f"Created channel {name} with ID {channel_id}")
            
            return channel_id
            
        except SlackApiError as e:
            logger.error(f"Slack API error creating channel: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating channel: {e}")
            return None
    
    async def archive_channel(self, channel_id: str) -> bool:
        """Archive a Slack channel."""
        try:
            await self.async_client.conversations_archive(channel=channel_id)
            
            logger.info(f"Archived channel {channel_id}")
            return True
            
        except SlackApiError as e:
            logger.error(f"Slack API error archiving channel: {e}")
            return False
        except Exception as e:
            logger.error(f"Error archiving channel: {e}")
            return False
    
    async def get_workspace_info(self) -> Dict[str, Any]:
        """Get information about the Slack workspace."""
        try:
            response = await self.async_client.team_info()
            return response["team"]
            
        except SlackApiError as e:
            logger.error(f"Slack API error getting workspace info: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error getting workspace info: {e}")
            return {}
    
    async def search_messages(
        self,
        query: str,
        count: int = 20,
        sort: str = "timestamp",
        sort_dir: str = "desc"
    ) -> List[SlackMessage]:
        """Search for messages across the workspace."""
        try:
            response = await self.async_client.search_messages(
                query=query,
                count=count,
                sort=sort,
                sort_dir=sort_dir
            )
            
            messages = []
            for match in response["messages"]["matches"]:
                message = SlackMessage(
                    message_id=match["ts"],
                    channel_id=match["channel"]["id"],
                    user_id=match.get("user", "Unknown"),
                    text=match.get("text", ""),
                    timestamp=match["ts"],
                    thread_ts=match.get("thread_ts"),
                    attachments=match.get("attachments"),
                    blocks=match.get("blocks")
                )
                messages.append(message)
            
            return messages
            
        except SlackApiError as e:
            logger.error(f"Slack API error searching messages: {e}")
            return []
        except Exception as e:
            logger.error(f"Error searching messages: {e}")
            return []
    
    def validate_webhook_signature(
        self,
        body: str,
        signature: str,
        timestamp: str
    ) -> bool:
        """Validate Slack webhook signature."""
        try:
            import hmac
            import hashlib
            
            # Create the signature base string
            sig_basestring = f"v0:{timestamp}:{body}"
            
            # Create the expected signature
            expected_signature = "v0=" + hmac.new(
                self.settings.slack_signing_secret.encode(),
                sig_basestring.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(expected_signature, signature)
            
        except Exception as e:
            logger.error(f"Error validating webhook signature: {e}")
            return False


# Global Slack client instance
_slack_client: Optional[SlackClient] = None


def get_slack_client() -> SlackClient:
    """Get the global Slack client instance."""
    global _slack_client
    
    if _slack_client is None:
        _slack_client = SlackClient()
    
    return _slack_client


async def send_slack_notification(
    channel: str,
    message: str,
    **kwargs
) -> Optional[str]:
    """Send a Slack notification."""
    client = get_slack_client()
    return await client.send_message(channel, message, **kwargs)


async def send_slack_dm(
    user_id: str,
    message: str,
    **kwargs
) -> Optional[str]:
    """Send a Slack direct message."""
    client = get_slack_client()
    return await client.send_dm(user_id, message, **kwargs) 