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
# Removed circular import: from src.services.db_services.db_manager import DateTimeEncoder

# Define DateTimeEncoder locally to avoid circular import
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            # Always convert to ISO 8601 format without timezone
            return obj.isoformat()
        elif isinstance(obj, Enum):
            return obj.value
        return super().default(obj)

# Initialize logger
logger = get_logger(__name__)

class MessageManager:
    """
    Message manager for storing and retrieving messages.
    
    This class provides functionality for:
    1. Adding messages to conversations
    2. Retrieving messages from conversations
    3. Searching for similar messages
    
    Terminology clarification:
    - 'Message' refers to the full object with metadata that's passed around the system
    - 'content' is the actual text/data in a message (stored in the 'content' column)
    - Database table 'swarm_messages' has 'content' column for the actual message text,
      but does not have a 'role' column (role is derived from 'sender' instead)
    
    It works with the DatabaseManager class for conversation management.
    """
    
    def __init__(self, supabase_client: Client):
        """
        Initialize the message manager with a Supabase client.
        
        Args:
            supabase_client: An initialized Supabase client
        """
        self.supabase = supabase_client
        self._error_count = 0
        
        # Initialize LLM service for embeddings
        ollama_url = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
        embedding_model = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
        self.llm_service = LLMService(ollama_url, embedding_model)
    
    def get_next_uuid(self) -> str:
        """Generate a unique UUID string for request IDs."""
        try:
            return str(uuid.uuid4())
        except Exception as e:
            logger.error(f"Error generating UUID: {str(e)}")
            self._error_count += 1
            # Fallback to timestamp-based ID if UUID generation fails
            return f"id-{int(time.time())}-{random.randint(1000, 9999)}"
            
    def add_message(self, session_id: Union[int, str], role: str, content: str, metadata: Optional[Dict[str, Any]] = None, 
                   embedding: Optional[List[float]] = None, request_id: Optional[str] = None, 
                   sender: Optional[str] = None, target: Optional[str] = None, user_id: Optional[str] = None) -> str:
        """
        Add a message to the database.
        
        Important note on terminology:
        - 'content' is the actual text/data of the message (LLM response, user input, etc.)
          and is stored in the 'content' column of the database
        - 'role' helps determine the message type (user/assistant/system/tool), but is not
          directly stored in the database (it's derived from 'sender' when retrieving)

        Note on database:  table is named swarm_messages
        columns:
        - id - unique message id
        - session_id - id of the session this message belongs to
        - timestamp - timestamp of the message
        - sender - sender id
        - target - target id
        - content - message content
        - metadata - metadata associated with the message
        - embedding_nomic - embedding of the message
        - user_id - user id
        
        Args:
            session_id: The session ID for this message (integer)
            role: The role of the message sender (user, assistant, system, tool)
            content: The message content (actual text/data being communicated)
            metadata: Optional metadata for the message
            embedding: Optional pre-calculated embedding
            request_id: Optional request ID for tool/agent calls (UUID string)
            sender: Sender ID (in dot notation)
            target: Target/receiver ID (in dot notation)
            user_id: User ID
            
        Returns:
            str: The request ID for this message or call (UUID string)
        """
        try:
            # Check database connectivity
            try:
                # Simple test query to verify connection
                test_query = self.supabase.table('swarm_messages').select('id').limit(1).execute()
                logger.debug(f"Database connection test: {test_query.data is not None}")
            except Exception as db_error:
                logger.warning(f"Database connection test failed: {db_error}")
            
            # Validate message content - don't allow empty messages
            logger.debug(f"Adding message to database: role={role}, content={content}, session_id={session_id}, sender={sender}, target={target}, user_id={user_id}")
            if not content or not content.strip():
                logger.warning(f"Attempted to add empty message to database (role: {role}, session: {session_id})")
                return request_id or ""
                
            # Convert session_id to integer if it's a string containing an integer
            if isinstance(session_id, str):
                try:
                    session_id = int(session_id)
                except ValueError:
                    # If not a valid int, keep as is
                    pass
            
            # Calculate embedding if not provided
            if embedding is None:
                try:
                    embedding = self.llm_service.get_embedding(content)
                except Exception as e:
                    logger.warning(f"Could not generate embedding for message: {e}")
                    # Provide default embedding (all zeros)
                    embedding = [0.0] * 768
            
            # Ensure metadata exists
            if metadata is None:
                metadata = {}
            
            # Ensure user_id is present
            if not user_id:
                user_id = "developer"  # Default user_id
                
            # Also store user_id in metadata for consistency
            if not metadata.get("user_id"):
                metadata["user_id"] = user_id
            
            # Handle request_id for tool/agent calls
            is_tool_call = role == "tool" or metadata.get("type") == "tool_result"
            
            # If no request_id provided and this is a tool call, get next request_id
            if request_id is None and is_tool_call:
                request_id = self.get_next_uuid()  # This should return a UUID string
            
            # Add request_id to metadata if it exists
            if request_id is not None:
                metadata["request_id"] = request_id
            
            # Add timestamp to metadata if not present
            current_time = timestamp()
            if "timestamp" not in metadata:
                metadata["timestamp"] = current_time
                
            # Generate default sender if not provided
            if not sender:
                if role == "user":
                    sender = "orchestrator_graph.cli"
                elif role == "assistant":
                    sender = "orchestrator_graph.llm"
                elif role == "tool":
                    tool_name = metadata.get("tool", "unknown")
                    sender = f"orchestrator_graph.{tool_name}_tool"
                else:
                    sender = "orchestrator_graph.system"
            
            # Generate default target if not provided
            if not target:
                if role == "user":
                    target = "orchestrator_graph.llm"
                elif role == "assistant":
                    target = "orchestrator_graph.cli"
                elif role == "tool":
                    target = "orchestrator_graph.llm"
                else:
                    target = "orchestrator_graph.cli"  # Default to client
            
            # Insert message - use column names that match the existing schema
            try:
                # Ensure we have a valid database connection
                if not self._ensure_connection():
                    logger.error("Could not ensure database connection - cannot insert message")
                    return request_id or ""
                
                # Using the exact column names from the existing schema
                message_data = {
                    'session_id': session_id,
                    'sender': sender,
                    'target': target,
                    'content': content,
                    'metadata': json.dumps(metadata, cls=DateTimeEncoder) if metadata else None,
                    'embedding_nomic': embedding,
                    'user_id': user_id,
                    'timestamp': current_time
                }
                
                logger.debug(f"Inserting message with data: session_id={session_id}, sender={sender}, target={target}, content_length={len(content)}")
                response = self.supabase.table('swarm_messages').insert(message_data).execute()
                
                if response.data:
                    logger.debug(f"Inserted message into session {session_id}, response data: {response.data}")
                else:
                    logger.warning(f"No data returned when inserting message for session {session_id}, response: {response}")
                    
            except Exception as e:
                # Log the detailed error for debugging
                logger.error(f"Error inserting message into database: {str(e)}")
                logger.error(f"Message details: session_id={session_id}, role={role}, user_id={user_id}")
                logger.error(f"Full exception details:", exc_info=True)
                # Re-raise to let the caller handle the error
                raise
            
            return request_id or ""  # Return request_id for tracking in calling code
        except Exception as e:
            logger.error(f"Error in add_message: {str(e)}")
            self._error_count += 1
            return request_id or ""

    def get_recent_messages(self, session_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent messages for a conversation.
        
        Args:
            session_id: The session ID to get messages for
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of messages with role and content fields
        """
        try:
            logger.debug(f"Getting recent messages for session {session_id}")
            
            response = self.supabase.table('swarm_messages')\
                .select('sender, target, content, metadata, timestamp')\
                .eq('session_id', session_id)\
                .order('timestamp', desc=True)\
                .limit(limit)\
                .execute()
            
            logger.debug(f"Retrieved {len(response.data) if response.data else 0} messages")
            
            # Return messages with standardized format
            result = []
            for item in response.data:
                sender = item.get('sender', '')
                # Derive role from sender
                role = "user"
                if "orchestrator_graph.llm" in sender or sender.endswith(".llm"):
                    role = "assistant"
                elif "system" in sender:
                    role = "system"
                elif "tool" in sender:
                    role = "tool"
                
                result.append({
                    'role': role,
                    'sender': sender,
                    'target': item.get('target'),
                    'content': item.get('content'),
                    'metadata': item.get('metadata', {}),
                    'timestamp': item.get('timestamp')
                })
            return result
        except Exception as e:
            logger.error(f"Error retrieving recent messages: {e}")
            return []

    def get_conversation_messages(self, session_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get all messages for a specific conversation.
        
        Args:
            session_id: The session ID to get messages for
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of messages with role and content fields
        """
        try:
            logger.debug(f"Getting all messages for session {session_id}")
            
            response = self.supabase.table('swarm_messages')\
                .select('sender, target, content, metadata, timestamp')\
                .eq('session_id', session_id)\
                .order('timestamp')\
                .limit(limit)\
                .execute()
            
            logger.debug(f"Retrieved {len(response.data) if response.data else 0} messages")
            
            # Return messages with standardized format
            result = []
            for item in response.data:
                sender = item.get('sender', '')
                # Derive role from sender
                role = "user"
                if "orchestrator_graph.llm" in sender or sender.endswith(".llm"):
                    role = "assistant"
                elif "system" in sender:
                    role = "system"
                elif "tool" in sender:
                    role = "tool"
                
                result.append({
                    'role': role,
                    'sender': sender,
                    'target': item.get('target'),
                    'content': item.get('content'),
                    'metadata': item.get('metadata', {}),
                    'timestamp': item.get('timestamp')
                })
            return result
        except Exception as e:
            logger.error(f"Error retrieving conversation messages: {e}")
            return []

    def search_similar_messages(self, embedding: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for messages similar to the given embedding.
        
        Args:
            embedding: Vector embedding to search for
            limit: Maximum number of results to return
            
        Returns:
            List of similar messages with content and metadata
        """
        try:
            response = self.supabase.rpc(
                'match_messages',
                {
                    'query_embedding': embedding,
                    'match_threshold': 0.7,
                    'match_count': limit
                }
            ).execute()
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Error searching similar messages: {e}")
            return []
            
    def store_message(self, session_id: str, role: str, content: str, sender: str, target: str, user_id: str = "developer") -> bool:
        """
        Store a message in a conversation with minimal required parameters.
        Simplified interface for BaseAgent to use.
        
        Note on fields:
        - 'content' is the actual text/data of the message that will be stored in the database
        - 'role' is the message type which is not directly stored but derived from 'sender'
        - 'sender' and 'target' are required and stored directly in the database

        Note on database:  table is named swarm_messages
        columns:
        - id - unique message id
        - session_id - id of the session this message belongs to
        - timestamp - timestamp of the message
        - sender - sender id
        - target - target id
        - content - message content
        - metadata - metadata associated with the message
        - embedding_nomic - embedding of the message
        - user_id - user id
        
        Args:
            session_id: The session ID for this message
            role: The role of the message sender
            content: The message content (actual text being communicated)
            sender: Sender ID (in dot notation)
            target: Target/receiver ID (in dot notation)
            user_id: User ID (defaults to "developer")
            
        Returns:
            bool: True if successfully stored, False otherwise
        """
        logger.debug(f"message_manager.store_message: Storing message: session_id={session_id}, role={role}, sender={sender}, target={target}, user_id={user_id}")
        try:
            # Ensure we have a valid database connection
            if not self._ensure_connection():
                logger.error("Could not ensure database connection - cannot store message")
                return False
                
            # Additional logging to verify session_id
            if not session_id:
                logger.error("Cannot store message - session_id is empty or None")
                return False
            
            message_id = self.add_message(
                session_id=session_id,
                role=role,
                content=content,
                sender=sender,
                target=target,
                user_id=user_id
            )
            
            result = message_id is not None and message_id != ""
            logger.info(f"message_manager.store_message: Result of storing message: {result}")
            return result
        except Exception as e:
            logger.error(f"Error in simplified message storage: {e}")
            logger.error(f"Exception details:", exc_info=True)
            return False
            
    def get_messages_by_session(self, session_id: Union[int, str], format_type: str = "raw", 
                              limit: int = 100, reverse: bool = False) -> List[Dict[str, Any]]:
        """
        Get messages for a session with different format options.
        
        Args:
            session_id: The session ID to get messages for
            format_type: Format type - "raw" (full data), "standard" (role/content only), 
                        or "chat" (formatted for chat history)
            limit: Maximum number of messages to retrieve
            reverse: Whether to return messages in reverse order (newest first)
            
        Returns:
            List of messages in the requested format
        """
        try:
            # First get the raw messages
            messages = self.get_conversation_messages(session_id, limit)
            
            # Skip processing if no messages or raw format requested
            if not messages or format_type == "raw":
                return messages if not reverse else list(reversed(messages))
                
            # Process based on format type
            if format_type == "standard":
                # Simple role/content format
                result = []
                for msg in messages:
                    result.append({
                        'role': msg.get('sender', '').split('.')[-1],  # Extract last part of sender
                        'content': msg.get('content', '')
                    })
                return result if not reverse else list(reversed(result))
                
            elif format_type == "chat":
                # Chat history format with timestamps and formatting
                result = []
                for msg in messages:
                    timestamp_str = msg.get('timestamp', '')
                    try:
                        dt = parse_datetime(timestamp_str)
                        time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        time_str = timestamp_str
                        
                    sender = msg.get('sender', '').split('.')[-1]
                    role = "User" if sender == "cli" else sender.capitalize()
                    
                    result.append({
                        'timestamp': time_str,
                        'role': role,
                        'content': msg.get('content', ''),
                        'metadata': msg.get('metadata', {}),
                    })
                return result if not reverse else list(reversed(result))
            
            # Default to raw with warning
            logger.warning(f"Unknown format type: {format_type}, returning raw messages")
            return messages if not reverse else list(reversed(messages))
            
        except Exception as e:
            logger.error(f"Error retrieving formatted messages: {e}")
            return [] 

    def _ensure_connection(self):
        """Ensure the database connection is valid before executing operations."""
        try:
            # Try a simple query to test the connection
            test = self.supabase.table('swarm_messages').select('id').limit(1).execute()
            logger.debug("Database connection is valid")
            return True
        except Exception as e:
            logger.warning(f"Database connection test failed: {e}")
            
            # Try to recreate the connection using environment variables
            try:
                url = os.getenv("SUPABASE_URL")
                key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
                
                if url and key:
                    logger.debug("Attempting to recreate database connection")
                    self.supabase = create_client(url, key)
                    
                    # Test the new connection
                    test = self.supabase.table('swarm_messages').select('id').limit(1).execute()
                    logger.debug("Successfully recreated database connection")
                    return True
                else:
                    logger.error("Missing database connection parameters (SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY)")
                    return False
            except Exception as reconnect_err:
                logger.error(f"Failed to recreate database connection: {reconnect_err}")
                return False 