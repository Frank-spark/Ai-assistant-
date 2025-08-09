"""AI Chain for Reflex Executive Assistant."""

import logging
import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta

from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain.memory import ConversationBufferWindowMemory
from langchain.tools import BaseTool
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

from ..config import get_settings
from ..integrations.slack_client import get_slack_client
from ..integrations.gmail_client import get_gmail_client
from ..integrations.asana_client import get_asana_client
from ..kb.retriever import get_kb_retriever
from ..storage.db import get_db_session
from ..storage.models import Conversation, Message, ToolUsage

logger = logging.getLogger(__name__)


class ReflexAIChain:
    """Main AI chain for Reflex Executive Assistant."""
    
    def __init__(self):
        self.settings = get_settings()
        self.llm = ChatOpenAI(
            model=self.settings.openai_model,
            temperature=self.settings.openai_temperature,
            openai_api_key=self.settings.openai_api_key
        )
        
        # Initialize tools
        self.tools = self._initialize_tools()
        
        # Initialize memory
        self.memory = ConversationBufferWindowMemory(
            memory_key="chat_history",
            return_messages=True,
            k=10
        )
        
        # Initialize prompt template
        self.prompt = self._create_prompt()
        
        # Initialize agent
        self.agent = create_openai_functions_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt
        )
        
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            memory=self.memory,
            verbose=self.settings.debug_mode,
            max_iterations=5,
            early_stopping_method="generate"
        )
        
        # Initialize knowledge base retriever
        self.kb_retriever = get_kb_retriever()
        
        logger.info("ReflexAIChain initialized successfully")
    
    def _initialize_tools(self) -> List[BaseTool]:
        """Initialize available tools."""
        tools = []
        
        # Email tools
        tools.append(EmailTool())
        tools.append(EmailSearchTool())
        tools.append(EmailComposeTool())
        
        # Slack tools
        tools.append(SlackMessageTool())
        tools.append(SlackChannelTool())
        tools.append(SlackUserTool())
        
        # Asana tools
        tools.append(AsanaTaskTool())
        tools.append(AsanaProjectTool())
        tools.append(AsanaCommentTool())
        
        # Calendar tools
        tools.append(CalendarTool())
        tools.append(MeetingTool())
        
        # Knowledge base tools
        tools.append(KnowledgeBaseTool())
        tools.append(CompanyContextTool())
        
        # Utility tools
        tools.append(DateTimeTool())
        tools.append(WebSearchTool())
        
        logger.info(f"Initialized {len(tools)} tools")
        return tools
    
    def _create_prompt(self) -> ChatPromptTemplate:
        """Create the system prompt template."""
        system_prompt = """You are Reflex, an AI executive assistant for Spark Robotic. You help executives manage their workflow, communications, and tasks efficiently.

Your capabilities include:
- Processing emails, Slack messages, and Asana updates
- Managing calendar and meetings
- Creating and updating tasks and projects
- Providing company context and knowledge
- Coordinating between different platforms

Your personality:
- Professional but approachable
- Proactive in identifying and solving problems
- Respectful of time and priorities
- Clear and concise in communication
- Follows company policies and constraints

Company Context:
- Spark Robotic is a robotics company
- Focus on efficiency and innovation
- Respect for time and deadlines
- Collaborative team environment

When responding:
1. Understand the user's request
2. Use appropriate tools to gather information
3. Take action if requested and within your capabilities
4. Provide clear, actionable responses
5. Follow up on any commitments made

Remember: You are here to make executives more productive and organized."""

        return ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
    
    async def process_slack_message(
        self,
        message: str,
        user_id: str,
        channel_id: str,
        team_id: str,
        workflow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process a Slack message and generate a response."""
        try:
            logger.info(f"Processing Slack message: {message}")
            
            # Store conversation
            conversation = await self._store_conversation(
                platform="slack",
                user_id=user_id,
                channel_id=channel_id,
                team_id=team_id,
                message=message,
                workflow_id=workflow_id
            )
            
            # Add context about the user and channel
            context = await self._get_slack_context(user_id, channel_id, team_id)
            
            # Process with AI
            response = await self.agent_executor.ainvoke({
                "input": f"Slack message from user {user_id} in channel {channel_id}: {message}\n\nContext: {context}",
                "chat_history": []
            })
            
            ai_response = response.get("output", "I'm sorry, I couldn't process that request.")
            
            # Store AI response
            await self._store_message(
                conversation_id=conversation.id,
                content=ai_response,
                sender="assistant",
                message_type="ai_response"
            )
            
            # Send response to Slack
            slack_client = get_slack_client()
            await slack_client.send_message(
                channel=channel_id,
                text=ai_response
            )
            
            logger.info(f"Successfully processed Slack message, response sent")
            
            return {
                "success": True,
                "response": ai_response,
                "conversation_id": conversation.id,
                "workflow_id": workflow_id
            }
            
        except Exception as e:
            logger.error(f"Error processing Slack message: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "workflow_id": workflow_id
            }
    
    async def process_email(
        self,
        email_data: Dict[str, Any],
        user_id: str,
        workflow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process an email and take appropriate actions."""
        try:
            logger.info(f"Processing email: {email_data.get('subject', 'No subject')}")
            
            # Store conversation
            conversation = await self._store_conversation(
                platform="gmail",
                user_id=user_id,
                message=email_data.get('subject', ''),
                workflow_id=workflow_id
            )
            
            # Analyze email content
            subject = email_data.get('subject', '')
            body = email_data.get('body', '')
            sender = email_data.get('from', '')
            
            # Process with AI
            response = await self.agent_executor.ainvoke({
                "input": f"Email received:\nSubject: {subject}\nFrom: {sender}\nBody: {body}\n\nPlease analyze this email and take appropriate actions.",
                "chat_history": []
            })
            
            ai_response = response.get("output", "I'm sorry, I couldn't process that email.")
            
            # Store AI response
            await self._store_message(
                conversation_id=conversation.id,
                content=ai_response,
                sender="assistant",
                message_type="ai_response"
            )
            
            logger.info(f"Successfully processed email")
            
            return {
                "success": True,
                "response": ai_response,
                "conversation_id": conversation.id,
                "workflow_id": workflow_id
            }
            
        except Exception as e:
            logger.error(f"Error processing email: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "workflow_id": workflow_id
            }
    
    async def process_asana_update(
        self,
        event_data: Dict[str, Any],
        user_id: str,
        workflow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process an Asana update and take appropriate actions."""
        try:
            logger.info(f"Processing Asana update: {event_data.get('action', 'Unknown action')}")
            
            # Store conversation
            conversation = await self._store_conversation(
                platform="asana",
                user_id=user_id,
                message=f"Asana {event_data.get('action', 'update')}",
                workflow_id=workflow_id
            )
            
            # Process with AI
            response = await self.agent_executor.ainvoke({
                "input": f"Asana update received:\n{json.dumps(event_data, indent=2)}\n\nPlease analyze this update and take appropriate actions.",
                "chat_history": []
            })
            
            ai_response = response.get("output", "I'm sorry, I couldn't process that Asana update.")
            
            # Store AI response
            await self._store_message(
                conversation_id=conversation.id,
                content=ai_response,
                sender="assistant",
                message_type="ai_response"
            )
            
            logger.info(f"Successfully processed Asana update")
            
            return {
                "success": True,
                "response": ai_response,
                "conversation_id": conversation.id,
                "workflow_id": workflow_id
            }
            
        except Exception as e:
            logger.error(f"Error processing Asana update: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "workflow_id": workflow_id
            }
    
    async def _get_slack_context(self, user_id: str, channel_id: str, team_id: str) -> str:
        """Get context about the Slack user and channel."""
        try:
            slack_client = get_slack_client()
            
            # Get user info
            user_info = await slack_client.get_user_info(user_id)
            user_name = user_info.get('name', 'Unknown User')
            user_title = user_info.get('profile', {}).get('title', '')
            
            # Get channel info
            channel_info = await slack_client.get_channel_info(channel_id)
            channel_name = channel_info.get('name', 'Unknown Channel')
            channel_purpose = channel_info.get('purpose', {}).get('value', '')
            
            context = f"User: {user_name} ({user_title})\nChannel: #{channel_name}\nPurpose: {channel_purpose}"
            
            return context
            
        except Exception as e:
            logger.warning(f"Could not get Slack context: {e}")
            return f"User: {user_id}, Channel: {channel_id}"
    
    async def _store_conversation(
        self,
        platform: str,
        user_id: str,
        message: str,
        channel_id: Optional[str] = None,
        team_id: Optional[str] = None,
        workflow_id: Optional[str] = None
    ) -> Conversation:
        """Store a new conversation in the database."""
        try:
            db_session = get_db_session()
            
            conversation = Conversation(
                platform=platform,
                user_id=user_id,
                channel_id=channel_id,
                team_id=team_id,
                workflow_id=workflow_id,
                started_at=datetime.utcnow(),
                status="active"
            )
            
            db_session.add(conversation)
            db_session.commit()
            
            # Store the initial message
            await self._store_message(
                conversation_id=conversation.id,
                content=message,
                sender="user",
                message_type="user_input"
            )
            
            return conversation
            
        except Exception as e:
            logger.error(f"Error storing conversation: {e}", exc_info=True)
            raise
    
    async def _store_message(
        self,
        conversation_id: int,
        content: str,
        sender: str,
        message_type: str
    ) -> Message:
        """Store a message in the database."""
        try:
            db_session = get_db_session()
            
            message = Message(
                conversation_id=conversation_id,
                content=content,
                sender=sender,
                message_type=message_type,
                timestamp=datetime.utcnow()
            )
            
            db_session.add(message)
            db_session.commit()
            
            return message
            
        except Exception as e:
            logger.error(f"Error storing message: {e}", exc_info=True)
            raise
    
    async def get_conversation_history(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get conversation history for a user."""
        try:
            db_session = get_db_session()
            
            conversations = db_session.query(Conversation).filter(
                Conversation.user_id == user_id
            ).order_by(Conversation.started_at.desc()).limit(limit).all()
            
            history = []
            for conv in conversations:
                messages = db_session.query(Message).filter(
                    Message.conversation_id == conv.id
                ).order_by(Message.timestamp.asc()).all()
                
                history.append({
                    "conversation_id": conv.id,
                    "platform": conv.platform,
                    "started_at": conv.started_at.isoformat(),
                    "messages": [
                        {
                            "sender": msg.sender,
                            "content": msg.content,
                            "timestamp": msg.timestamp.isoformat()
                        }
                        for msg in messages
                    ]
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}", exc_info=True)
            return []


# Tool implementations
class EmailTool(BaseTool):
    name = "email_tool"
    description = "Send emails to specified recipients"
    
    async def _arun(self, to: str, subject: str, body: str) -> str:
        try:
            gmail_client = get_gmail_client()
            result = await gmail_client.send_email(to, subject, body)
            return f"Email sent successfully to {to}"
        except Exception as e:
            return f"Failed to send email: {str(e)}"


class EmailSearchTool(BaseTool):
    name = "email_search_tool"
    description = "Search for emails based on criteria"
    
    async def _arun(self, query: str, max_results: int = 10) -> str:
        try:
            gmail_client = get_gmail_client()
            results = await gmail_client.search_emails(query, max_results)
            return f"Found {len(results)} emails matching '{query}'"
        except Exception as e:
            return f"Failed to search emails: {str(e)}"


class EmailComposeTool(BaseTool):
    name = "email_compose_tool"
    description = "Compose and draft emails"
    
    async def _arun(self, to: str, subject: str, body: str) -> str:
        try:
            gmail_client = get_gmail_client()
            result = await gmail_client.compose_email(to, subject, body)
            return f"Email draft created successfully"
        except Exception as e:
            return f"Failed to create email draft: {str(e)}"


class SlackMessageTool(BaseTool):
    name = "slack_message_tool"
    description = "Send messages to Slack channels or users"
    
    async def _arun(self, channel: str, message: str) -> str:
        try:
            slack_client = get_slack_client()
            result = await slack_client.send_message(channel, message)
            return f"Message sent successfully to {channel}"
        except Exception as e:
            return f"Failed to send Slack message: {str(e)}"


class SlackChannelTool(BaseTool):
    name = "slack_channel_tool"
    description = "Get information about Slack channels"
    
    async def _arun(self, channel_id: str) -> str:
        try:
            slack_client = get_slack_client()
            info = await slack_client.get_channel_info(channel_id)
            return f"Channel: {info.get('name', 'Unknown')}, Purpose: {info.get('purpose', {}).get('value', 'None')}"
        except Exception as e:
            return f"Failed to get channel info: {str(e)}"


class SlackUserTool(BaseTool):
    name = "slack_user_tool"
    description = "Get information about Slack users"
    
    async def _arun(self, user_id: str) -> str:
        try:
            slack_client = get_slack_client()
            info = await slack_client.get_user_info(user_id)
            return f"User: {info.get('name', 'Unknown')}, Title: {info.get('profile', {}).get('title', 'None')}"
        except Exception as e:
            return f"Failed to get user info: {str(e)}"


class AsanaTaskTool(BaseTool):
    name = "asana_task_tool"
    description = "Create, update, or get information about Asana tasks"
    
    async def _arun(self, action: str, task_data: Dict[str, Any]) -> str:
        try:
            asana_client = get_asana_client()
            if action == "create":
                result = await asana_client.create_task(task_data)
                return f"Task created successfully: {result.get('gid', 'Unknown')}"
            elif action == "update":
                result = await asana_client.update_task(task_data['gid'], task_data)
                return f"Task updated successfully"
            elif action == "get":
                result = await asana_client.get_task(task_data['gid'])
                return f"Task: {result.get('name', 'Unknown')}"
            else:
                return f"Unknown action: {action}"
        except Exception as e:
            return f"Failed to perform Asana task action: {str(e)}"


class AsanaProjectTool(BaseTool):
    name = "asana_project_tool"
    description = "Create, update, or get information about Asana projects"
    
    async def _arun(self, action: str, project_data: Dict[str, Any]) -> str:
        try:
            asana_client = get_asana_client()
            if action == "create":
                result = await asana_client.create_project(project_data)
                return f"Project created successfully: {result.get('gid', 'Unknown')}"
            elif action == "update":
                result = await asana_client.update_project(project_data['gid'], project_data)
                return f"Project updated successfully"
            elif action == "get":
                result = await asana_client.get_project(project_data['gid'])
                return f"Project: {result.get('name', 'Unknown')}"
            else:
                return f"Unknown action: {action}"
        except Exception as e:
            return f"Failed to perform Asana project action: {str(e)}"


class AsanaCommentTool(BaseTool):
    name = "asana_comment_tool"
    description = "Add comments to Asana tasks or projects"
    
    async def _arun(self, resource_type: str, resource_id: str, comment: str) -> str:
        try:
            asana_client = get_asana_client()
            result = await asana_client.add_comment(resource_type, resource_id, comment)
            return f"Comment added successfully to {resource_type} {resource_id}"
        except Exception as e:
            return f"Failed to add comment: {str(e)}"


class CalendarTool(BaseTool):
    name = "calendar_tool"
    description = "Manage calendar events and availability"
    
    async def _arun(self, action: str, event_data: Dict[str, Any]) -> str:
        try:
            # TODO: Implement calendar integration
            return f"Calendar {action} requested for {event_data.get('summary', 'Unknown event')}"
        except Exception as e:
            return f"Failed to perform calendar action: {str(e)}"


class MeetingTool(BaseTool):
    name = "meeting_tool"
    description = "Schedule and manage meetings"
    
    async def _arun(self, action: str, meeting_data: Dict[str, Any]) -> str:
        try:
            # TODO: Implement meeting scheduling
            return f"Meeting {action} requested for {meeting_data.get('title', 'Unknown meeting')}"
        except Exception as e:
            return f"Failed to perform meeting action: {str(e)}"


class KnowledgeBaseTool(BaseTool):
    name = "knowledge_base_tool"
    description = "Search the company knowledge base for information"
    
    async def _arun(self, query: str) -> str:
        try:
            # TODO: Implement knowledge base search
            return f"Knowledge base search for: {query}"
        except Exception as e:
            return f"Failed to search knowledge base: {str(e)}"


class CompanyContextTool(BaseTool):
    name = "company_context_tool"
    description = "Get company context and policies"
    
    async def _arun(self, context_type: str) -> str:
        try:
            # TODO: Implement company context retrieval
            return f"Company context for: {context_type}"
        except Exception as e:
            return f"Failed to get company context: {str(e)}"


class DateTimeTool(BaseTool):
    name = "datetime_tool"
    description = "Get current date and time information"
    
    async def _arun(self, timezone: str = "UTC") -> str:
        try:
            now = datetime.utcnow()
            return f"Current time (UTC): {now.strftime('%Y-%m-%d %H:%M:%S')}"
        except Exception as e:
            return f"Failed to get datetime: {str(e)}"


class WebSearchTool(BaseTool):
    name = "web_search_tool"
    description = "Search the web for current information"
    
    async def _arun(self, query: str) -> str:
        try:
            # TODO: Implement web search
            return f"Web search for: {query}"
        except Exception as e:
            return f"Failed to perform web search: {str(e)}"


# Global instance
_ai_chain_instance = None


def get_ai_chain() -> ReflexAIChain:
    """Get the global AI chain instance."""
    global _ai_chain_instance
    if _ai_chain_instance is None:
        _ai_chain_instance = ReflexAIChain()
    return _ai_chain_instance 