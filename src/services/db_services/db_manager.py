import logging
import os
import json
import time
import uuid
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
from enum import Enum

from dotenv import load_dotenv
from supabase import create_client, Client

from src.services.logging_services.logging_service import get_logger
from src.services.logging_services.http_logging import configure_http_client_logging
from src.utils.datetime_utils import format_datetime, parse_datetime, now, timestamp
from src.services.llm_services.llm_service import LLMService
from src.services.db_services.message_manager import MessageManager

# Initialize logger
logger = get_logger(__name__)

# Enums and classes for state management
class TaskStatus(Enum):
    """Status values for tasks/requests."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class MessageRole:
    """Standard message role constants."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"

class Message:
    """Simple message container."""
    def __init__(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        self.role = role
        self.content = content
        self.metadata = metadata or {}

# Exceptions for state management
class StateError(Exception):
    """Exception for state-related errors."""
    pass

class StateTransitionError(StateError):
    """Exception for invalid state transitions."""
    pass

# Custom JSON encoder to handle datetime serialization
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            # Always convert to ISO 8601 format without timezone
            return obj.isoformat()
        elif isinstance(obj, Enum):
            return obj.value
        return super().default(obj)

load_dotenv(override=True)

class DatabaseManager:
    """
    Database manager for storing and retrieving messages.
    
    This class provides a simple interface for:
    1. Creating and retrieving conversations
    2. Storing and retrieving messages
    3. Managing conversation metadata
    
    It does NOT handle state management, which is left to LangGraph.
    """
    
    def __init__(self):
        """Initialize the database manager with Supabase connection."""
        url: str = os.getenv("SUPABASE_URL")
        key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        self.supabase: Client = create_client(url, key)
        self._last_update = now()
        self._update_count = 0
        self._error_count = 0
        
        # Initialize message manager for message operations
        self.message_manager = MessageManager(self.supabase)

    def get_next_id(self, column_name: str, table_name: str) -> int:
        """Fetch the next ID by incrementing the current maximum for a given column and table."""
        try:
            # Use a direct SQL-like approach that doesn't rely on the 'max' foreign key relationship
            response = self.supabase.from_(table_name).select(column_name).execute()
            
            max_val = 0
            if response.data:
                for item in response.data:
                    val = item.get(column_name, 0)
                    if val is None:
                        continue
                    if isinstance(val, str) and val.isdigit():
                        val = int(val)
                    if isinstance(val, int) and val > max_val:
                        max_val = val
            
            return max_val + 1
            
        except Exception as e:
            logger.error(f"Error getting next ID: {e}")
            return 1  # Default to 1 on error

    def create_conversation(self, user_id: str, title: Optional[str] = None) -> int:
        """
        Create a new conversation and return its ID.
        
        Args:
            user_id: The user ID for this conversation
            title: Optional title for the conversation
            
        Returns:
            int: Session ID of the new conversation
        """
        # Ensure user_id is valid
        if not user_id:
            user_id = "developer"  # Default user_id
            
        # Get next session ID as integer
        try:
            next_session_id = self.get_next_id('session_id', 'swarm_messages')
        except Exception as e:
            logger.error(f"Error getting next session ID: {e}")
            # Fallback to a random integer
            next_session_id = int(time.time())
        
        # Create timestamp
        now_str = timestamp()
        
        # Create a default embedding vector (768 dimensions of zeros)
        default_embedding = [0.0] * 768
        
        # Insert conversation start record using Supabase API
        try:
            # Build metadata JSON
            metadata_json = {
                "title": title,
                "created_at": now_str,
                "updated_at": now_str,
                "user_id": user_id,
                "is_conversation_start": True
            }
            
            # Insert system message to mark conversation start
            self.message_manager.add_message(
                session_id=next_session_id,
                role="system",
                content="User starting new conversation",
                metadata=metadata_json,
                embedding=default_embedding,
                user_id=user_id
            )
            
            logger.debug(f"Successfully created conversation with ID: {next_session_id}")
        except Exception as e:
            logger.error(f"Error creating conversation: {str(e)}")
            self._error_count += 1
        
        return next_session_id

    def list_conversations(self, user_id: Optional[str] = None) -> dict:
        """
        List conversations with their metadata, optionally filtered by user ID.
        
        Args:
            user_id: Optional user ID to filter conversations by
        
        Returns:
            dict: Dictionary mapping session IDs to conversation metadata
        """
        try:
            # Query all system messages to find conversation starts
            response = self.supabase.table('swarm_messages')\
                .select('session_id, metadata, timestamp, user_id')\
                .order('timestamp')\
                .execute()
            
            conversations = {}
            # First pass - collect all unique session IDs
            unique_sessions = set()
            for item in response.data:
                session_id = item.get('session_id')
                if session_id and session_id not in unique_sessions:
                    unique_sessions.add(session_id)
            
            # Process each unique session
            for session_id in unique_sessions:
                # Find the first message (likely system) for this session
                init_message = self.supabase.table('swarm_messages')\
                    .select('metadata, timestamp, user_id')\
                    .eq('session_id', session_id)\
                    .order('timestamp')\
                    .limit(1)\
                    .execute()
                
                if not init_message.data or len(init_message.data) == 0:
                    continue
                
                item = init_message.data[0]
                
                # Get metadata
                metadata_str = item.get('metadata', '{}')
                try:
                    metadata = json.loads(metadata_str) if isinstance(metadata_str, str) else metadata_str
                except json.JSONDecodeError:
                    metadata = {}
                
                # Get title from metadata - don't use a default name
                name = metadata.get('title')
                
                # Get created timestamp
                timestamp_str = item.get('timestamp')
                created_at = parse_datetime(timestamp_str)
                
                # Make sure it's timezone-naive
                if created_at and hasattr(created_at, 'tzinfo') and created_at.tzinfo:
                    created_at = created_at.replace(tzinfo=None)
                
                # Find the most recent message for this session_id
                latest_message = self.supabase.table('swarm_messages')\
                    .select('timestamp')\
                    .eq('session_id', session_id)\
                    .order('timestamp', desc=True)\
                    .limit(1)\
                    .execute()
                
                # Set updated_at to the latest message timestamp or created_at as fallback
                if latest_message.data and len(latest_message.data) > 0:
                    updated_at = parse_datetime(latest_message.data[0].get('timestamp'))
                    # Make sure it's timezone-naive
                    if updated_at and hasattr(updated_at, 'tzinfo') and updated_at.tzinfo:
                        updated_at = updated_at.replace(tzinfo=None)
                else:
                    updated_at = created_at
                
                # Get user ID from item or metadata
                item_user_id = item.get('user_id', 'developer')
                metadata_user_id = metadata.get('user_id')
                conversation_user_id = metadata_user_id or item_user_id
                
                # Skip if filtering by user_id and this conversation doesn't belong to the user
                if user_id and conversation_user_id != user_id:
                    continue
                
                conversations[session_id] = {
                    'name': name,
                    'description': metadata.get('description', ''),
                    'created_at': created_at,
                    'updated_at': updated_at,
                    'user_id': conversation_user_id
                }
                
                # Log for debugging
                logger.debug(f"Found conversation: ID={session_id}, Name={name}, User={conversation_user_id}, Updated={updated_at}")
            
            user_filter_msg = f" for user '{user_id}'" if user_id else ""
            logger.debug(f"Retrieved {len(conversations)} conversations{user_filter_msg}")
            return conversations
        except Exception as e:
            logger.error(f"Error retrieving conversations: {e}")
            return {}

    def rename_conversation(self, session_id: int, new_title: str) -> bool:
        """
        Rename an existing conversation.
        
        Args:
            session_id: The ID of the conversation to rename
            new_title: The new title for the conversation
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Convert session_id to integer if it's a string
            if isinstance(session_id, str):
                try:
                    session_id = int(session_id)
                except ValueError:
                    logger.error(f"Invalid session ID format: {session_id}")
                    return False
            
            # Find the system message that contains the conversation metadata
            try:
                # Find the initial system message
                system_message = self.supabase.table('swarm_messages') \
                    .select('id, metadata') \
                    .eq('session_id', session_id) \
                    .eq('sender', 'orchestrator_graph.system') \
                    .order('timestamp') \
                    .limit(1) \
                    .execute()
                    
                if system_message.data and len(system_message.data) > 0:
                    # Get the message ID and current metadata
                    message_id = system_message.data[0].get('id')
                    metadata_str = system_message.data[0].get('metadata', '{}')
                    
                    try:
                        current_metadata = json.loads(metadata_str) if isinstance(metadata_str, str) else metadata_str
                    except json.JSONDecodeError:
                        current_metadata = {}
                    
                    # Update the metadata with the new title
                    current_metadata['title'] = new_title
                    current_metadata['updated_at'] = timestamp()
                    
                    # Update the metadata in the database
                    self.supabase.table('swarm_messages') \
                        .update({'metadata': json.dumps(current_metadata, cls=DateTimeEncoder)}) \
                        .eq('id', message_id) \
                        .execute()
                        
                    logger.debug(f"Successfully renamed conversation {session_id} to '{new_title}'")
                    return True
                else:
                    logger.error(f"Cannot rename conversation {session_id}: start message not found")
                    return False
                
            except Exception as e:
                logger.error(f"Error updating conversation title in database: {e}")
                return False
            
        except Exception as e:
            logger.error(f"Error renaming conversation: {e}")
            return False

    def start_conversation(self, user_id: str, title: Optional[str] = None) -> int:
        """
        Start a new conversation with a system message.
        
        Args:
            user_id: The user ID for this conversation
            title: Optional title for the conversation
            
        Returns:
            int: The session ID of the new conversation, or 0 if failed
        """
        try:
            # Create new conversation
            session_id = self.create_conversation(user_id, title)
            if session_id:
                logger.debug(f"Started conversation with ID: {session_id}")
                return session_id
            else:
                logger.error("Failed to create conversation")
                return 0
        except Exception as e:
            logger.error(f"Error starting conversation: {e}")
            return 0

    def continue_conversation(self, session_id: str, user_id: str = "developer") -> Dict[str, Any]:
        """
        Continue an existing conversation. Verifies it exists and returns metadata.
        
        Args:
            session_id: The session ID to continue
            user_id: The user ID requesting the conversation
            
        Returns:
            Dict with conversation metadata or empty dict if not found/accessible
        """
        try:
            # Convert session_id to integer if appropriate
            if isinstance(session_id, str):
                try:
                    session_id = int(session_id)
                except ValueError:
                    pass  # Keep as string if not convertible
                    
            # Get conversation details
            conversations = self.list_conversations(user_id)
            conversation = conversations.get(session_id)
            
            if not conversation:
                logger.error(f"Conversation {session_id} not found or not accessible by user {user_id}")
                return {}
                
            logger.debug(f"Continued conversation with ID: {session_id}")
            return conversation
            
        except Exception as e:
            logger.error(f"Error continuing conversation: {e}")
            return {}

    def get_conversation(self, session_id: Union[int, str]) -> Dict[str, Any]:
        """
        Get a conversation by ID.
        
        Args:
            session_id: The ID of the conversation to get
            
        Returns:
            Dict with conversation metadata or empty dict if not found
        """
        try:
            # Convert session_id to integer if it's a string
            if isinstance(session_id, str):
                try:
                    session_id = int(session_id)
                except ValueError:
                    pass  # Keep as string if not convertible
            
            # Use list_conversations but filter for just this ID
            conversations = self.list_conversations()
            return conversations.get(session_id, {})
            
        except Exception as e:
            logger.error(f"Error getting conversation: {e}")
            return {}
            
    def delete_conversation(self, session_id: Union[int, str]) -> bool:
        """
        Delete a conversation and all its messages.
        
        Args:
            session_id: The ID of the conversation to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Convert session_id to integer if it's a string
            if isinstance(session_id, str):
                try:
                    session_id = int(session_id)
                except ValueError:
                    logger.error(f"Invalid session ID format: {session_id}")
                    return False
                    
            # Delete all messages for this session
            self.supabase.table('swarm_messages') \
                .delete() \
                .eq('session_id', session_id) \
                .execute()
                
            logger.debug(f"Deleted conversation with ID: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting conversation: {e}")
            return False

