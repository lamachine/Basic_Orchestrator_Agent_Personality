import logging

# Configure HTTP client logging to use file handlers and not console output
httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.DEBUG)
httpx_logger.propagate = False  # Prevent propagation to root logger/console

urllib3_logger = logging.getLogger("urllib3")
urllib3_logger.setLevel(logging.DEBUG)
urllib3_logger.propagate = False

requests_logger = logging.getLogger("requests")
requests_logger.setLevel(logging.DEBUG)
requests_logger.propagate = False

http_client_logger = logging.getLogger("http.client")
http_client_logger.setLevel(logging.DEBUG)
http_client_logger.propagate = False

aiohttp_logger = logging.getLogger("aiohttp")
aiohttp_logger.setLevel(logging.DEBUG)
aiohttp_logger.propagate = False

import os
from supabase import create_client, Client
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
from dotenv import load_dotenv
import json
from ollama import Client
from pydantic import BaseModel, Field, model_validator
import logging
from enum import Enum
import time
import uuid
import random

# Import state management components
from src.state.state_models import MessageRole, TaskStatus, Message
from src.state.state_errors import StateError, ValidationError, StateUpdateError, StateTransitionError
from src.state.state_validator import StateValidator

# Initialize logger
logger = logging.getLogger(__name__)

# Custom JSON encoder to handle datetime serialization
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            # Always convert to ISO 8601 format without timezone
            return obj.replace(tzinfo=None).isoformat()
        elif isinstance(obj, Enum):
            return obj.value
        return super().default(obj)

# Define Pydantic models for conversation state management
class ConversationMetadata(BaseModel):
    """Metadata for a conversation."""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    user_id: str
    title: Optional[str] = None
    description: Optional[str] = None

# Extended database-specific Message class with additional fields
class DBMessage(Message):
    """Extended Message class with database-specific fields."""
    sender: str  # Required field for the message sender
    target: str  # Required field for the message target
    
    # Helper method to format agent ID with namespace
    @staticmethod
    def format_agent_id(component: str, subcomponent: str) -> str:
        """Format agent ID using dot notation hierarchy.
        
        Args:
            component: Main component (e.g., 'orchestrator_graph')
            subcomponent: Subcomponent (e.g., 'valet_tool')
            
        Returns:
            Formatted agent ID (e.g., 'orchestrator_graph.valet_tool')
        """
        return f"{component}.{subcomponent}"

class ConversationState(BaseModel):
    """State of a conversation."""
    session_id: int
    metadata: ConversationMetadata
    current_request_id: Optional[str] = None
    messages: List[DBMessage] = Field(default_factory=list)
    current_task_status: TaskStatus = Field(default=TaskStatus.PENDING)
    
    @model_validator(mode='before')
    @classmethod
    def update_timestamp(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Update the timestamp when the state is modified."""
        if isinstance(values, dict):
            values['metadata'] = values.get('metadata', {})
            if isinstance(values['metadata'], dict):
                values['metadata']['updated_at'] = datetime.now()
        return values
    
    @property
    def user_id(self) -> str:
        """Get the user ID for this conversation."""
        return self.metadata.user_id
    
    def add_message(self, role: MessageRole, content: str, metadata: Optional[Dict[str, Any]] = None) -> DBMessage:
        """Add a message to the conversation.
        
        Note: This is maintained for backward compatibility. For new code, create a Message object
        directly and append it to the messages list.
        """
        # Derive sender and target based on role
        if role == MessageRole.USER:
            sender = "orchestrator_graph.cli"
            target = "orchestrator_graph.llm"
        elif role == MessageRole.ASSISTANT:
            sender = "orchestrator_graph.llm"
            target = "orchestrator_graph.cli"
        elif role == MessageRole.TOOL:
            tool_name = metadata.get("tool", "unknown") if metadata else "unknown"
            sender = f"orchestrator_graph.{tool_name}_tool"
            target = "orchestrator_graph.llm"
        else:  # SYSTEM or other
            sender = "orchestrator_graph.system"
            target = "orchestrator_graph.cli"
            
        message = DBMessage(
            role=role,
            content=content,
            metadata=metadata or {},
            sender=sender,
            target=target
        )
        self.messages.append(message)
        self.metadata.updated_at = datetime.now()
        return message
    
    def get_last_message(self) -> Optional[DBMessage]:
        """Get the last message in the conversation."""
        return self.messages[-1] if self.messages else None
    
    def get_context_window(self, n: int = 5) -> List[DBMessage]:
        """Get the last n messages for context."""
        return self.messages[-n:] if self.messages else []

class ConversationSummary(BaseModel):
    """Summary information about a conversation."""
    session_id: Union[int, str]  # Allow either int or string session IDs
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    message_count: int
    user_id: str
    current_task_status: TaskStatus = TaskStatus.PENDING
    display_name: Optional[str] = None  # Field for formatted display name

# Use the imported StateValidator directly

load_dotenv(override=True)

class DatabaseManager:
    def __init__(self):
        url: str = os.getenv("SUPABASE_URL")
        key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        self.supabase: Client = create_client(url, key)
        self.validator = StateValidator()
        self._last_update = datetime.now()
        self._update_count = 0
        self._error_count = 0

    def _check_rate_limit(self) -> None:
        """Prevent too frequent updates"""
        current_time = datetime.now()
        if (current_time - self._last_update) < timedelta(milliseconds=100):
            self._update_count += 1
            if self._update_count > 100:  # Arbitrary limit
                raise StateUpdateError("Too many rapid state updates")
        else:
            self._update_count = 0
        self._last_update = current_time

    def initialize_conversation(self, user_id: str, title: Optional[str] = None) -> ConversationState:
        """Create a new conversation in the database.
        
        Args:
            user_id: The user ID for the conversation
            title: Optional title for the conversation
            
        Returns:
            The initialized conversation state
        """
        try:
            metadata = ConversationMetadata(user_id=user_id, title=title)
            # Insert metadata first
            result = self.supabase.table('conversations').insert({
                'user_id': user_id,
                'title': title,
                'created_at': metadata.created_at.isoformat(),
                'updated_at': metadata.updated_at.isoformat()
            }).execute()
            
            data = result.data
            if not data or len(data) == 0:
                raise StateUpdateError("Failed to create conversation")
                
            session_id = data[0]['id']
            return ConversationState(
                session_id=session_id,
                metadata=metadata
            )
        except Exception as e:
            self._error_count += 1
            logger.error(f"Error initializing conversation: {str(e)}")
            raise StateUpdateError(f"Failed to initialize conversation: {str(e)}")
            
    def get_conversation(self, session_id: int) -> ConversationState:
        """Retrieve a conversation by ID.
        
        Args:
            session_id: The session ID to retrieve
            
        Returns:
            The conversation state
        """
        try:
            # Get conversation metadata
            conv_result = self.supabase.table('conversations').select('*').eq('id', session_id).execute()
            if not conv_result.data or len(conv_result.data) == 0:
                raise StateError(f"No conversation found with ID {session_id}")
                
            conv_data = conv_result.data[0]
            
            # Get messages for this conversation
            msg_result = self.supabase.table('messages').select('*').eq('conversation_id', session_id).order('created_at').execute()
            
            # Create metadata
            metadata = ConversationMetadata(
                user_id=conv_data['user_id'],
                title=conv_data.get('title'),
                description=conv_data.get('description'),
                created_at=datetime.fromisoformat(conv_data['created_at']),
                updated_at=datetime.fromisoformat(conv_data['updated_at'])
            )
            
            # Create conversation state
            state = ConversationState(
                session_id=session_id,
                metadata=metadata,
                current_request_id=conv_data.get('current_request_id'),
                current_task_status=TaskStatus(conv_data.get('current_task_status', TaskStatus.PENDING))
            )
            
            # Add messages to state
            for msg_data in msg_result.data:
                msg_content = msg_data.get('content', '')
                role = MessageRole(msg_data.get('role', 'system'))
                msg_metadata = msg_data.get('metadata')
                msg_metadata_dict = json.loads(msg_metadata) if msg_metadata else {}
                
                message = DBMessage(
                    role=role,  # For backward compatibility
                    content=msg_content,
                    metadata=msg_metadata_dict,
                    created_at=datetime.fromisoformat(msg_data['created_at']),
                    sender=msg_data.get('sender', 'system'),
                    target=msg_data.get('target', 'user')
                )
                state.messages.append(message)
                
            return state
            
        except Exception as e:
            self._error_count += 1
            logger.error(f"Error retrieving conversation: {str(e)}")
            if isinstance(e, StateError):
                raise
            raise StateError(f"Failed to retrieve conversation: {str(e)}")
    
    def save_conversation(self, state: ConversationState) -> bool:
        """Save the conversation state to the database.
        
        Args:
            state: The conversation state to save
            
        Returns:
            True if successful, False otherwise. Doesn't raise exceptions.
        """
        try:
            self._check_rate_limit()
            
            # Validate state before saving
            if not self.validator.validate_message_sequence(state.messages):
                logger.error("Invalid message sequence in conversation")
                return False
            
            # Make sure all datetime objects are timezone-naive
            state.metadata.created_at = self._ensure_naive_datetime(state.metadata.created_at)
            state.metadata.updated_at = self._ensure_naive_datetime(state.metadata.updated_at)
            
            # Find the system message that contains the conversation metadata
            try:
                # Find the initial system message
                system_message = self.supabase.table('swarm_messages') \
                    .select('id, metadata') \
                    .eq('session_id', state.session_id) \
                    .eq('sender', 'orchestrator_graph.system') \
                    .order('timestamp', desc=False) \
                    .limit(1) \
                    .execute()
                    
                if system_message.data and len(system_message.data) > 0:
                    # Get the message ID and current metadata
                    message_id = system_message.data[0].get('id')
                    current_metadata = json.loads(system_message.data[0].get('metadata', '{}'))
                    
                    # Update the metadata with the conversation state
                    current_metadata['title'] = state.metadata.title
                    current_metadata['updated_at'] = datetime.now().isoformat()
                    current_metadata['current_task_status'] = state.current_task_status
                    if state.current_request_id:
                        current_metadata['current_request_id'] = state.current_request_id
                    
                    # Update the metadata in the database
                    self.supabase.table('swarm_messages') \
                        .update({'metadata': json.dumps(current_metadata, cls=DateTimeEncoder)}) \
                        .eq('id', message_id) \
                        .execute()
                        
                    logger.debug(f"Updated conversation metadata for session {state.session_id}")
            except Exception as metadata_error:
                logger.error(f"Error updating conversation metadata: {str(metadata_error)}")
                # Continue with saving messages even if metadata update fails
            
            # Process any messages that haven't been saved to the database yet
            for message in state.messages:
                # Skip messages that already have a database ID
                if message.metadata.get('db_id'):
                    continue
                
                try:
                    # Create a default embedding vector (768 dimensions of zeros)
                    default_embedding = [0.0] * 768
                    
                    # Prepare the message data
                    msg_data = {
                        'session_id': state.session_id,
                        'user_id': state.metadata.user_id,
                        'content': message.content,
                        'sender': message.sender,
                        'target': message.target,
                        'timestamp': message.created_at.isoformat(),
                        'metadata': json.dumps(message.metadata, cls=DateTimeEncoder),
                        'embedding_nomic': default_embedding  # Required field
                    }
                    
                    # Insert the message
                    result = self.supabase.table('swarm_messages').insert(msg_data).execute()
                    
                    # Update the message metadata with the database ID
                    if result.data and len(result.data) > 0:
                        message.metadata['db_id'] = result.data[0].get('id')
                        logger.debug(f"Inserted new message with ID {message.metadata['db_id']}")
                except Exception as msg_error:
                    logger.error(f"Error saving message: {str(msg_error)}")
                    # Continue with other messages
            
            return True
            
        except Exception as e:
            self._error_count += 1
            logger.error(f"Error in save_conversation: {str(e)}")
            return False  # Return False instead of raising an exception
            
    def list_conversations(self, user_id: Optional[str] = None) -> dict:
        """List conversations with their metadata, optionally filtered by user ID.
        
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
                created_at = self._safe_parse_timestamp(timestamp_str)
                
                # Find the most recent message for this session_id
                latest_message = self.supabase.table('swarm_messages')\
                    .select('timestamp')\
                    .eq('session_id', session_id)\
                    .order('timestamp', desc=True)\
                    .limit(1)\
                    .execute()
                
                # Set updated_at to the latest message timestamp or created_at as fallback
                if latest_message.data and len(latest_message.data) > 0:
                    updated_at = self._safe_parse_timestamp(latest_message.data[0].get('timestamp'))
                else:
                    updated_at = created_at
                
                # Format timestamps as naive datetimes
                created_at = self._ensure_naive_datetime(created_at)
                updated_at = self._ensure_naive_datetime(updated_at)
                
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
            
    def delete_conversation(self, session_id: int) -> bool:
        """Delete a conversation.
        
        Args:
            session_id: The session ID to delete
            
        Returns:
            True if successful, raises exception otherwise
        """
        try:
            # First delete all messages
            self.supabase.table('messages').delete().eq('conversation_id', session_id).execute()
            
            # Then delete the conversation
            self.supabase.table('conversations').delete().eq('id', session_id).execute()
            
            return True
            
        except Exception as e:
            self._error_count += 1
            logger.error(f"Error deleting conversation: {str(e)}")
            raise StateUpdateError(f"Failed to delete conversation: {str(e)}")
    
    def add_message_to_conversation(self, session_id: int, message: DBMessage) -> bool:
        """Add a message to an existing conversation.
        
        Args:
            session_id: The session ID to add the message to
            message: The message to add
            
        Returns:
            True if successful, raises exception otherwise
        """
        try:
            # Get current state
            state = self.get_conversation(session_id)
            
            # Add message
            state.messages.append(message)
            
            # Save updated state
            return self.save_conversation(state)
            
        except Exception as e:
            self._error_count += 1
            logger.error(f"Error adding message: {str(e)}")
            if isinstance(e, StateError):
                raise
            raise StateUpdateError(f"Failed to add message: {str(e)}")
    
    def update_task_status(self, conversation: ConversationState, new_status: TaskStatus) -> bool:
        """Update the task status for a conversation.
        
        Args:
            conversation: The conversation state to update
            new_status: The new task status
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate transition
            if not self.validator.validate_task_transition(conversation.current_task_status, new_status):
                logger.warning(f"Invalid task status transition: {conversation.current_task_status} -> {new_status}")
                return False
            
            # Update status
            conversation.current_task_status = new_status
            
            # Save updated state
            return self.save_conversation(conversation)
            
        except Exception as e:
            self._error_count += 1
            logger.error(f"Error updating task status: {str(e)}")
            return False

    def get_errors(self) -> int:
        """Get the number of errors encountered."""
        return self._error_count

    def get_next_uuid(self) -> str:
        """Generate a unique UUID string for request IDs.
        
        Returns:
            str: A new UUID string
        """
        try:
            return str(uuid.uuid4())
        except Exception as e:
            logger.error(f"Error generating UUID: {str(e)}")
            self._error_count += 1
            # Fallback to timestamp-based ID if UUID generation fails
            return f"id-{int(time.time())}-{random.randint(1000, 9999)}"

    def get_next_id(self, column_name: str, table_name: str) -> int:
        """Fetch the next ID by incrementing the current maximum for a given column and table."""
        try:
            # Use a simpler query to get the max value
            response = self.supabase.table(table_name).select(column_name).execute()
            
            # Find the max value from the returned data
            max_val = 0
            if response.data:
                for item in response.data:
                    if column_name in item and item[column_name] is not None:
                        # Safely convert to int, handling string values
                        try:
                            if isinstance(item[column_name], str):
                                # If it's a numeric string, convert it
                                if item[column_name].isdigit():
                                    val = int(item[column_name])
                                else:
                                    continue  # Skip non-numeric strings
                            else:
                                val = int(item[column_name])
                            max_val = max(max_val, val)
                        except (ValueError, TypeError):
                            # Skip values that can't be converted to int
                            continue
                        
            return max_val + 1  # Increment by 1 for the next ID
        except Exception as e:
            logger.error(f"Error getting next ID: {str(e)}")
            self._error_count += 1
            return 1  # Default to 1 on error

    def create_conversation(self, user_id: str, title: Optional[str] = None) -> ConversationState:
        """Create a new conversation and return its state.
        
        Args:
            user_id: The user ID for this conversation
            title: Optional title for the conversation
            
        Returns:
            ConversationState: The state of the new conversation
        """
        # Ensure user_id is valid
        if not user_id:
            user_id = "developer"  # Default user_id
            
        # Get next session ID
        next_session_id = self.get_next_id('session_id', 'swarm_messages')
        
        # Create timestamp
        now = datetime.now()
        
        # Create metadata
        metadata = ConversationMetadata(
            created_at=now,
            updated_at=now,
            user_id=user_id,
            title=title  # Don't create a default title
        )
        
        # Create conversation state
        conversation = ConversationState(
            session_id=next_session_id,
            metadata=metadata,
            current_task_status=TaskStatus.PENDING
        )
        
        # Create a default embedding vector (768 dimensions of zeros)
        default_embedding = [0.0] * 768
        
        # Insert conversation start record using Supabase API
        try:
            # First check which columns actually exist in the table
            columns_info = self.supabase.table('swarm_messages').select('*').limit(1).execute()
            sample_record = {}
            if columns_info.data and len(columns_info.data) > 0:
                sample_record = columns_info.data[0]
            
            # Build insert data based on actual columns
            insert_data = {
                'session_id': next_session_id,
                'user_id': user_id,
                'timestamp': now.isoformat(),
                'content': 'User starting new conversation',  # More descriptive content
                'metadata': json.dumps(metadata.dict(), cls=DateTimeEncoder),
                'sender': 'orchestrator_graph.system',
                'target': 'orchestrator_graph.cli',
                'embedding_nomic': default_embedding  # Add the required embedding
            }
            
            # Only include the 'type' field if it exists in the schema
            if 'type' in sample_record:
                insert_data['type'] = 'conversation_start'
            
            self.supabase.table('swarm_messages').insert(insert_data).execute()
            logger.debug(f"Successfully created conversation with ID: {next_session_id}")
        except Exception as e:
            logger.error(f"Error creating conversation: {str(e)}")
            self._error_count += 1
        
        return conversation

    def load_conversation(self, session_id: str, filter_messages: bool = True, 
                         limit: Optional[int] = 100, message_limit: Optional[int] = None) -> Optional[ConversationState]:
        """Loads a conversation from the database.
        
        Args:
            session_id: The session ID for the conversation
            filter_messages: Whether to filter messages by user_id
            limit: Limit on the number of total messages to retrieve
            message_limit: Limit on the number of latest messages to retrieve
        
        Returns:
            Optional[ConversationState]: The conversation state if found, None otherwise
        """
        try:
            # Query conversation metadata
            conversation = self.supabase.from_('swarm_conversations').select('*').eq('session_id', session_id).single().execute()
            
            if not conversation.data:
                logging.warning(f"No conversation found with session ID {session_id}")
                raise ValueError(f"No conversation found with session ID {session_id}")

            # Create metadata from database row
            conversation_data = conversation.data
            metadata = ConversationMetadata(
                name=conversation_data.get('name', 'Unnamed'),
                description=conversation_data.get('description', ''),
                created_at=self._ensure_naive_datetime(conversation_data.get('created_at')),
                updated_at=self._ensure_naive_datetime(conversation_data.get('updated_at')),
                user_id=conversation_data.get('user_id', 'developer'),
                tags=json.loads(conversation_data.get('tags', '[]')) if conversation_data.get('tags') else [],
                settings=json.loads(conversation_data.get('settings', '{}')) if conversation_data.get('settings') else {},
                session_id=session_id
            )
            
            # Get messages
            messages_response = self.supabase.table('swarm_messages')\
                .select('sender, content, timestamp, metadata, target')\
                .eq('session_id', session_id)\
                .order('timestamp')\
                .execute()
            
            messages = []
            for msg_data in messages_response.data:
                msg_sender = msg_data.get('sender', '')
                msg_content = msg_data.get('content', '')
                msg_timestamp_str = msg_data.get('timestamp')
                msg_metadata_str = msg_data.get('metadata', '{}')
                msg_target = msg_data.get('target', 'orchestrator_graph.cli')
                
                # Parse timestamp
                try:
                    msg_timestamp = self._safe_parse_timestamp(msg_timestamp_str)
                except (ValueError, TypeError):
                    msg_timestamp = datetime.now()
                
                # Parse metadata
                try:
                    msg_metadata_dict = json.loads(msg_metadata_str) if isinstance(msg_metadata_str, str) else msg_metadata_str
                except (json.JSONDecodeError, TypeError):
                    msg_metadata_dict = {}
                
                # Determine the appropriate role based on sender
                if "cli" in msg_sender:
                    role = MessageRole.USER
                elif "llm" in msg_sender:
                    role = MessageRole.ASSISTANT
                elif "tool" in msg_sender:
                    role = MessageRole.TOOL
                else:
                    role = MessageRole.SYSTEM
                    
                message = DBMessage(
                    role=role,  # For backward compatibility
                    content=msg_content,
                    created_at=msg_timestamp,
                    metadata=msg_metadata_dict,
                    sender=msg_sender,
                    target=msg_target
                )
                messages.append(message)
            
            # Create conversation state
            state = ConversationState(
                session_id=session_id,
                metadata=metadata,
                messages=messages,
                current_task_status=TaskStatus(conversation_data.get('current_task_status', 'pending'))
            )
            
            return state
        except Exception as e:
            logger.error(f"Error loading conversation: {e}")
            return None

    def continue_conversation(self, session_id) -> Optional[ConversationState]:
        """Continue an existing conversation.
        
        Args:
            session_id: The session ID to continue (can be string or int)
            
        Returns:
            Optional[ConversationState]: The conversation state if found, None otherwise
        """
        try:
            self._check_rate_limit()
            
            # Debug log
            logger.debug(f"DB Manager continuing conversation with session ID: {session_id} (type: {type(session_id).__name__})")
            
            # Always convert session_id to string for consistency
            session_id_str = str(session_id)
            
            # First check if there are any messages with this session ID
            check_messages = self.supabase.table('swarm_messages')\
                .select('session_id')\
                .eq('session_id', session_id_str)\
                .limit(1)\
                .execute()
                
            if not check_messages.data or len(check_messages.data) == 0:
                logger.error(f"No messages found for session ID: {session_id_str}")
                return None
                
            # Get all messages for this session
            messages_query = self.supabase.table('swarm_messages')\
                .select('id, session_id, user_id, content, sender, target, metadata, timestamp')\
                .eq('session_id', session_id_str)\
                .order('timestamp')\
                .execute()
                
            if not messages_query.data or len(messages_query.data) == 0:
                logger.error(f"No messages found for session ID: {session_id_str}")
                return None
                
            # Get first message for metadata
            first_message = messages_query.data[0]
            
            # Parse metadata
            metadata_str = first_message.get('metadata', '{}')
            try:
                metadata_dict = json.loads(metadata_str) if isinstance(metadata_str, str) else metadata_str
            except json.JSONDecodeError:
                metadata_dict = {}
                
            # Create metadata
            metadata = ConversationMetadata(
                user_id=first_message.get('user_id', 'developer'),
                title=metadata_dict.get('title'),
                description=metadata_dict.get('description', ''),
                created_at=self._safe_parse_timestamp(first_message.get('timestamp')),
                updated_at=datetime.now()  # Set to current time as we're continuing
            )
            
            # Create messages list
            messages = []
            for msg in messages_query.data:
                # Parse message metadata
                msg_metadata_str = msg.get('metadata', '{}')
                try:
                    msg_metadata = json.loads(msg_metadata_str) if isinstance(msg_metadata_str, str) else msg_metadata_str
                except json.JSONDecodeError:
                    msg_metadata = {}
                    
                # Determine role from sender
                sender = msg.get('sender', '')
                if 'cli' in sender or 'user' in sender:
                    role = MessageRole.USER
                elif 'llm' in sender or 'assistant' in sender:
                    role = MessageRole.ASSISTANT
                elif 'tool' in sender:
                    role = MessageRole.TOOL
                else:
                    role = MessageRole.SYSTEM
                    
                # Create message
                message = DBMessage(
                    role=role,
                    content=msg.get('content', ''),
                    created_at=self._safe_parse_timestamp(msg.get('timestamp')),
                    metadata=msg_metadata,
                    sender=msg.get('sender', ''),
                    target=msg.get('target', '')
                )
                messages.append(message)
                
            # Create conversation state
            conversation = ConversationState(
                session_id=session_id_str,
                metadata=metadata,
                messages=messages,
                current_task_status=TaskStatus.PENDING
            )
            
            # Update timestamp to mark as active
            self._update_conversation_timestamp(session_id_str)
            
            logger.debug(f"Successfully loaded conversation with session ID: {session_id_str}, found {len(messages)} messages")
            return conversation
            
        except Exception as e:
            logger.error(f"Error continuing conversation: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
            
    def _update_conversation_timestamp(self, session_id: str) -> None:
        """Update the timestamp on a conversation to mark it as active.
        
        Args:
            session_id: The session ID to update
        """
        try:
            # Find the earliest message for this session
            earliest_message = self.supabase.table('swarm_messages') \
                .select('id') \
                .eq('session_id', session_id) \
                .eq('sender', 'orchestrator_graph.system') \
                .order('timestamp', desc=False) \
                .limit(1) \
                .execute()
                
            if earliest_message.data and len(earliest_message.data) > 0:
                message_id = earliest_message.data[0].get('id')
                
                # Update the timestamp of the first message
                self.supabase.table('swarm_messages') \
                    .update({'timestamp': datetime.now().isoformat()}) \
                    .eq('id', message_id) \
                    .execute()
                    
                logger.debug(f"Updated timestamp for conversation {session_id}")
            else:
                logger.warning(f"Could not find initial message for conversation {session_id}")
        except Exception as e:
            logger.error(f"Error updating conversation timestamp: {e}")

    def add_message(self, session_id: str, role: str, message: str, metadata: Optional[Dict[str, Any]] = None, 
                   embedding: Optional[List[float]] = None, request_id: Optional[str] = None, 
                   sender: Optional[str] = None, target: Optional[str] = None) -> str:
        """Enhanced add_message with metadata support, automatic embedding, and request ID handling.
        
        Args:
            session_id: The session ID for this message
            role: The role of the message sender (user, assistant, system, tool) - kept for backward compatibility
            message: The message content
            metadata: Optional metadata for the message
            embedding: Optional pre-calculated embedding
            request_id: Optional request ID for tool/agent calls
            sender: Sender ID (in dot notation)
            target: Target/receiver ID (in dot notation)
            user_id: User ID
            
        Returns:
            str: The request ID for this message or call
        """
        try:
            # Validate message content - don't allow empty messages
            if not message or not message.strip():
                logger.warning(f"Attempted to add empty message to database (role: {role}, session: {session_id})")
                return request_id or ""
                
            self._check_rate_limit()
            
            # Calculate embedding if not provided
            if embedding is None:
                embedding = self.calculate_embedding(message)
            
            # Ensure metadata exists
            if metadata is None:
                metadata = {}
            
            # Ensure user_id is present with "developer" as default
            if not metadata.get("user_id"):
                metadata["user_id"] = "developer"
            
            # Handle request_id for tool/agent calls
            try:
                message_role = MessageRole(role)
            except ValueError:
                # Default to SYSTEM for unknown roles
                message_role = MessageRole.SYSTEM
                
            is_tool_call = message_role == MessageRole.TOOL or metadata.get("type") == "tool_result"
            
            # If no request_id provided and this is a tool call, get next request_id
            if request_id is None and is_tool_call:
                request_id = self.get_next_uuid()
            
            # Add request_id to metadata if it exists
            if request_id is not None:
                metadata["request_id"] = request_id
            
            # Add timestamp to metadata if not present
            current_time = datetime.now().isoformat()
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
            
            # Insert message
            try:
                self.supabase.table('swarm_messages').insert({
                    'session_id': session_id,
                    'sender': sender,
                    'target': target,
                    'content': message,
                    'metadata': json.dumps(metadata, cls=DateTimeEncoder) if metadata else None,
                    'embedding_nomic': embedding,
                    'timestamp': current_time,
                    'user_id': metadata.get('user_id'),
                    'request_id': metadata.get('request_id')
                }).execute()
            except Exception as e:
                # Log the error but don't retry - let the caller handle any database errors
                logger.error(f"Error inserting message: {e}")
                raise
            
            return request_id or ""  # Return request_id for tracking in calling code
        except StateError as e:
            logger.error(f"State error adding message: {e}")
            return request_id or ""
        except Exception as e:
            logger.error(f"Error adding message: {e}")
            return request_id or ""

    def calculate_embedding(self, message: str) -> List[float]:
        """Calculate the embedding for a given message using Ollama API.
        
        Args:
            message: The text to embed
            
        Returns:
            List[float]: A 768-dimension vector representation of the text
        """
        try:
            # Initialize the Ollama client
            ollama_url = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
            client = Client(host=ollama_url)
            
            # Get the model to use for embeddings - use a default if not specified
            model = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
            
            # Generate the embedding using the embeddings method
            response = client.embeddings(model=model, prompt=message)
            
            # Extract the embedding vector from the response
            embedding = response.embedding
            
            return embedding
        except Exception as e:
            logger.error(f"Error calculating embedding: {e}")
            return [0.0] * 768  # Return zero vector on error with 768 dimensions

    def get_recent_messages(self, session_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent messages for a conversation.
        
        Args:
            session_id: The session ID to get messages for
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of messages with role and content fields
        """
        try:
            logger.debug(f"Getting recent messages for session {session_id}")
            
            response = self.supabase.table('swarm_messages')\
                .select('sender, content')\
                .eq('session_id', session_id)\
                .order('timestamp', desc=True)\
                .limit(limit)\
                .execute()
            
            logger.debug(f"Retrieved {len(response.data) if response.data else 0} messages")
            
            # Convert the column names back to what the rest of the code expects
            result = []
            for item in response.data:
                result.append({
                    'role': item['sender'],
                    'message': item['content']
                })
            return result
        except Exception as e:
            logger.error(f"Error retrieving recent messages: {e}")
            return []

    def search_similar_messages(self, embedding: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        response = self.supabase.rpc(
            'match_messages',
            {
                'query_embedding': embedding,
                'match_threshold': 0.7,
                'match_count': limit
            }
        ).execute()
        return response.data

    async def save_graph_state(self, conversation_id: str, state: Dict[str, Any]) -> None:
        """Save complete graph state to Supabase"""
        try:
            # Store the main state in the conversations table
            self.supabase.table('conversations').update({
                'current_task': state.get('current_task'),
                'task_history': json.dumps(state.get('task_history', []), cls=DateTimeEncoder),
                'agent_states': json.dumps(state.get('agent_states', {}), cls=DateTimeEncoder),
                'agent_results': json.dumps(state.get('agent_results', {}), cls=DateTimeEncoder),
                'final_result': state.get('final_result'),
                'updated_at': datetime.now().isoformat()
            }).eq('conversation_id', conversation_id).execute()

            # Store messages if they exist
            if messages := state.get('messages', []):
                for msg in messages:
                    self.add_message(
                        conversation_id,
                        msg.role.value,  # Using Enum value
                        msg.content,
                        metadata=msg.metadata
                    )
        except Exception as e:
            raise RuntimeError(f"Failed to save graph state: {str(e)}") from e

    async def load_graph_state(self, conversation_id: str) -> Dict[str, Any]:
        """Load complete graph state from Supabase"""
        # Get conversation state
        conv_response = self.supabase.table('conversations')\
            .select('*')\
            .eq('conversation_id', conversation_id)\
            .single()\
            .execute()
        
        if not conv_response.data:
            raise ValueError(f"No conversation found with id {conversation_id}")

        conv_data = conv_response.data

        # Get messages
        messages = self.get_recent_messages(conversation_id, limit=100)  # Adjust limit as needed

        # Reconstruct graph state
        return {
            'conversation_state': {
                'conversation_id': conversation_id,
                'messages': messages,
                'last_updated': conv_data.get('updated_at'),
                'current_task_status': conv_data.get('current_task_status', 'pending')
            },
            'messages': messages,
            'current_task': conv_data.get('current_task'),
            'task_history': json.loads(conv_data.get('task_history', '[]')),
            'agent_states': json.loads(conv_data.get('agent_states', '{}')),
            'agent_results': json.loads(conv_data.get('agent_results', '{}')),
            'final_result': conv_data.get('final_result')
        }

    async def update_agent_state(self, conversation_id: str, agent_id: str, state: Dict[str, Any]) -> None:
        """Update a specific agent's state"""
        # Get current agent states
        conv_response = self.supabase.table('conversations')\
            .select('agent_states')\
            .eq('conversation_id', conversation_id)\
            .single()\
            .execute()
        
        if not conv_response.data:
            raise ValueError(f"No conversation found with id {conversation_id}")

        # Update agent state
        agent_states = json.loads(conv_response.data.get('agent_states', '{}'))
        agent_states[agent_id] = state

        # Save back to database
        self.supabase.table('conversations').update({
            'agent_states': json.dumps(agent_states, cls=DateTimeEncoder),
            'updated_at': datetime.now().isoformat()
        }).eq('conversation_id', conversation_id).execute()

    async def get_conversation_history(
        self,
        conversation_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        role: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get conversation history with filters"""
        query = self.supabase.table('swarm_messages')\
            .select('*')\
            .eq('session_id', conversation_id)\
            .order('timestamp', desc=True)

        if start_date:
            query = query.gte('timestamp', start_date.isoformat())
        if end_date:
            query = query.lte('timestamp', end_date.isoformat())
        if role:
            query = query.eq('sender', role)

        response = query.limit(limit).execute()
        return response.data

    async def search_conversations(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search conversations using full-text search"""
        search_query = self.supabase.table('swarm_messages')\
            .select('*')\
            .textSearch('content', query)\
            .order('timestamp', desc=True)

        if conversation_id:
            search_query = search_query.eq('session_id', conversation_id)

        response = search_query.limit(limit).execute()
        return response.data

    async def get_agent_interactions(
        self,
        conversation_id: str,
        agent_id: str,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get interactions for a specific agent"""
        query = self.supabase.table('swarm_messages')\
            .select('*')\
            .eq('session_id', conversation_id)\
            .eq('metadata->>agent', agent_id)\
            .order('timestamp', desc=True)

        if status:
            query = query.eq('metadata->>status', status)

        response = query.limit(limit).execute()
        return response.data

    async def get_task_timeline(
        self,
        conversation_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get timeline of tasks and their status changes"""
        query = self.supabase.table('conversations')\
            .select('task_history')\
            .eq('conversation_id', conversation_id)\
            .single()\
            .execute()

        if not query.data:
            return []

        task_history = json.loads(query.data.get('task_history', '[]'))
        
        # Filter by date if specified
        if start_date or end_date:
            filtered_history = []
            for task in task_history:
                task_date = datetime.fromisoformat(task.split(':', 1)[0])
                if start_date and task_date < start_date:
                    continue
                if end_date and task_date > end_date:
                    continue
                filtered_history.append(task)
            return filtered_history

        return task_history

    async def get_conversation_summary(self, conversation_id: str) -> Dict[str, Any]:
        """Get a summary of conversation statistics and status"""
        # Get message counts by role
        message_counts = self.supabase.table('swarm_messages')\
            .select('sender, count(*)')\
            .eq('session_id', conversation_id)\
            .group('sender')\
            .execute()

        # Get latest state
        state = self.supabase.table('conversations')\
            .select('current_task, current_task_status, updated_at')\
            .eq('conversation_id', conversation_id)\
            .single()\
            .execute()

        # Get completed tasks count
        task_history = json.loads(state.data.get('task_history', '[]'))
        completed_tasks = len([t for t in task_history if 'COMPLETED' in t])

        return {
            'message_counts': message_counts.data,
            'current_task': state.data.get('current_task'),
            'current_status': state.data.get('current_task_status'),
            'last_updated': state.data.get('updated_at'),
            'completed_tasks': completed_tasks,
            'total_tasks': len(task_history)
        }

    def add_messages_to_conversation(self, session_id: int, messages: List[DBMessage]) -> bool:
        """
        Add multiple messages to an existing conversation.
        
        Args:
            session_id: The ID of the conversation to add messages to
            messages: List of Message objects to add
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            StateError: If the state cannot be updated
        """
        try:
            # First get the current conversation state
            conversation = self.get_conversation(session_id)
            if not conversation:
                logger.error(f"Cannot add messages to non-existent conversation: {session_id}")
                self._error_count += 1
                return False
                
            # Add each message to the conversation
            for message in messages:
                conversation.messages.append(message)
                
            # Save the updated conversation
            return self.save_conversation(conversation)
            
        except Exception as e:
            logger.error(f"Error adding messages to conversation {session_id}: {str(e)}")
            self._error_count += 1
            raise StateError(f"Failed to add messages to conversation: {str(e)}")
    
    def get_messages_for_session(self, session_id: int) -> List[DBMessage]:
        """
        Get all messages for a specific conversation session.
        
        Args:
            session_id: The ID of the session to get messages for
            
        Returns:
            List[DBMessage]: List of message objects
            
        Raises:
            StateError: If messages cannot be retrieved
        """
        try:
            # Query the database for messages
            response = self.supabase.table('messages').select('*').eq('conversation_id', session_id).order('created_at').execute()
            
            if response.data:
                # Convert to Message objects
                messages = []
                for msg_data in response.data:
                    try:
                        # Handle content as JSON if it's stored that way
                        content = msg_data.get('content')
                        if isinstance(content, str):
                            try:
                                content = json.loads(content)
                            except json.JSONDecodeError:
                                # Keep as string if not valid JSON
                                pass
                                
                        message = DBMessage(
                            role=MessageRole(msg_data.get('role', 'system')),
                            content=content,
                            created_at=datetime.fromisoformat(msg_data.get('created_at')) if isinstance(msg_data.get('created_at'), str) else msg_data.get('created_at'),
                            metadata=json.loads(msg_data.get('metadata', '{}')) if isinstance(msg_data.get('metadata'), str) else msg_data.get('metadata', {}),
                            sender=msg_data.get('sender', 'system'),
                            target=msg_data.get('target', 'user')
                        )
                        messages.append(message)
                    except Exception as e:
                        logger.error(f"Error parsing message data: {str(e)}")
                        self._error_count += 1
                
                return messages
            return []
            
        except Exception as e:
            logger.error(f"Error retrieving messages for session {session_id}: {str(e)}")
            self._error_count += 1
            raise StateError(f"Failed to get messages: {str(e)}")
    
    def clear_conversations(self, user_id: str = None) -> bool:
        """
        Clear all conversations for a user or all conversations if no user_id is provided.
        
        Args:
            user_id: Optional user ID to limit deletion to a specific user
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Begin a transaction
            if user_id:
                # Get all session IDs for this user
                response = self.supabase.table('conversations').select('id').eq('user_id', user_id).execute()
                if not response.data:
                    return True  # No conversations to delete
                
                session_ids = [item['id'] for item in response.data]
                
                # Delete messages for these sessions
                for session_id in session_ids:
                    self.supabase.table('messages').delete().eq('conversation_id', session_id).execute()
                
                # Delete metadata for these sessions
                self.supabase.table('conversations').delete().eq('user_id', user_id).execute()
            else:
                # Delete all messages
                self.supabase.table('messages').delete().neq('id', 0).execute()
                
                # Delete all metadata
                self.supabase.table('conversations').delete().neq('id', 0).execute()
                
            return True
            
        except Exception as e:
            logger.error(f"Error clearing conversations: {str(e)}")
            self._error_count += 1
            return False
    
    def get_conversation_count(self, user_id: str = None) -> int:
        """
        Get the count of conversations for a user or all conversations.
        
        Args:
            user_id: Optional user ID to limit count to a specific user
            
        Returns:
            int: Number of conversations
        """
        try:
            if user_id:
                response = self.supabase.table('conversations').select('id').eq('user_id', user_id).execute()
            else:
                response = self.supabase.table('conversations').select('id').execute()
                
            return len(response.data)
            
        except Exception as e:
            logger.error(f"Error getting conversation count: {str(e)}")
            self._error_count += 1
            return 0
    
    def update_message(self, message: DBMessage) -> bool:
        """
        Update a specific message in the database.
        
        Args:
            message: The Message object to update
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            StateError: If the message cannot be updated
        """
        if not message.metadata.get('db_id'):
            logger.error("Cannot update message without database ID")
            self._error_count += 1
            raise StateError("Message DB ID is required for updates")
            
        try:
            # Convert message to dict for database update
            message_data = {
                'role': message.role,
                'content': message.content,
                'metadata': json.dumps(message.metadata, cls=DateTimeEncoder),
                'sender': message.sender,
                'target': message.target
            }
            
            # Update the message in the database
            response = self.supabase.table('messages').update(message_data).eq('id', message.metadata['db_id']).execute()
            
            return len(response.data) > 0
            
        except Exception as e:
            logger.error(f"Error updating message {message.metadata.get('db_id')}: {str(e)}")
            self._error_count += 1
            raise StateError(f"Failed to update message: {str(e)}")
    
    def update_state(self, state: ConversationState) -> bool:
        """
        Update the full state of a conversation.
        
        Args:
            state: The ConversationState object to update
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            StateUpdateError: If the state cannot be updated
        """
        self._check_rate_limit()
            
        try:
            # Validate the state before updating
            if not self.validator.validate_message_sequence(state.messages):
                logger.error("Invalid message sequence for update")
                self._error_count += 1
                raise ValidationError("State validation failed")
                
            # Update conversation
            conversation_update = {
                'updated_at': state.metadata.updated_at.isoformat(),
                'title': state.metadata.title,
                'description': state.metadata.description,
                'current_task_status': state.current_task_status,
                'current_request_id': state.current_request_id
            }
            
            conversation_response = self.supabase.table('conversations').update(
                conversation_update
            ).eq('id', state.session_id).execute()
            
            if not conversation_response.data:
                logger.error(f"Failed to update conversation for session {state.session_id}")
                self._error_count += 1
                return False
                
            # Get existing messages to determine what needs to be added/updated
            existing_messages = self.get_messages_for_session(state.session_id)
            existing_ids = {msg.metadata.get('db_id') for msg in existing_messages if msg.metadata.get('db_id')}
            
            # Update existing messages and insert new ones
            for message in state.messages:
                db_id = message.metadata.get('db_id')
                if db_id and db_id in existing_ids:
                    self.update_message(message)
                else:
                    # This is a new message, add it
                    self.add_message_to_conversation(state.session_id, message)
                    
            return True
            
        except Exception as e:
            logger.error(f"Error updating state for session {state.session_id}: {str(e)}")
            self._error_count += 1
            raise StateUpdateError(f"Failed to update state: {str(e)}")

    # Add method to rename a conversation
    def rename_conversation(self, session_id: int, new_title: str) -> bool:
        """Rename an existing conversation.
        
        Args:
            session_id: The ID of the conversation to rename
            new_title: The new title for the conversation
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Load the conversation
            conversation = self.load_conversation(session_id)
            if not conversation:
                logger.error(f"Cannot rename conversation {session_id}: not found")
                return False
            
            # Update the title
            conversation.metadata.title = new_title
            conversation.metadata.updated_at = datetime.now()
            
            # Get the metadata as a dictionary
            metadata_dict = conversation.metadata.dict()
            
            # Update the conversation metadata in the database
            try:
                # First, get the conversation start message
                start_message = self.supabase.table('swarm_messages') \
                    .select('*') \
                    .eq('session_id', session_id) \
                    .eq('sender', 'orchestrator_graph.system') \
                    .execute()
                
                if start_message.data and len(start_message.data) > 0:
                    # Get the first message ID
                    message_id = start_message.data[0].get('id')
                    
                    # Get existing metadata
                    current_metadata = json.loads(start_message.data[0].get('metadata', '{}'))
                    
                    # Update the title
                    current_metadata['title'] = new_title
                    current_metadata['updated_at'] = datetime.now().isoformat()
                    
                    # Update the message
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

    def _safe_parse_timestamp(self, timestamp_str):
        """Safely parse a timestamp string into a datetime object.
        
        Args:
            timestamp_str: Timestamp string to parse
            
        Returns:
            datetime: Parsed datetime object, or current time if parsing fails
        """
        if not timestamp_str:
            return datetime.now()
            
        try:
            # Handle already parsed datetime objects
            if isinstance(timestamp_str, datetime):
                return timestamp_str.replace(tzinfo=None) if timestamp_str.tzinfo else timestamp_str

            # Handle string timestamps
            if isinstance(timestamp_str, str):
                # Split timestamp into parts before and after the decimal point if exists
                parts = timestamp_str.split('.')
                
                if len(parts) == 2:
                    # There's a decimal point - handle microseconds
                    base = parts[0]
                    fractional_part = parts[1]
                    
                    # Find timezone marker position
                    tz_pos = -1
                    for marker in ['+', '-']:
                        pos = fractional_part.find(marker)
                        if pos >= 0:
                            tz_pos = pos
                            break
                    
                    # Handle timezone
                    if tz_pos >= 0:
                        # Extract microseconds and timezone separately
                        micros = fractional_part[:tz_pos]
                        timezone = fractional_part[tz_pos:]
                        
                        # Truncate or pad microseconds to exactly 6 digits
                        if len(micros) > 6:
                            micros = micros[:6]  # Truncate if longer
                        else:
                            micros = micros.ljust(6, '0')  # Pad if shorter
                        
                        # Reconstruct ISO format with proper microseconds
                        timestamp_str = f"{base}.{micros}{timezone}"
                    else:
                        # No timezone in fractional part
                        if 'Z' in fractional_part:
                            # Handle 'Z' timezone marker
                            z_pos = fractional_part.find('Z')
                            micros = fractional_part[:z_pos]
                            
                            # Truncate or pad microseconds
                            if len(micros) > 6:
                                micros = micros[:6]
                            else:
                                micros = micros.ljust(6, '0')
                                
                            timestamp_str = f"{base}.{micros}Z"
                        else:
                            # No timezone markers at all
                            micros = fractional_part
                            
                            # Truncate or pad microseconds
                            if len(micros) > 6:
                                micros = micros[:6]
                            else:
                                micros = micros.ljust(6, '0')
                                
                            timestamp_str = f"{base}.{micros}"
                
                # Replace 'Z' timezone with +00:00 for compatibility
                timestamp_str = timestamp_str.replace('Z', '+00:00')
                
                try:
                    # Try parsing the formatted timestamp
                    dt = datetime.fromisoformat(timestamp_str)
                    
                    # Make it naive by removing timezone info
                    return dt.replace(tzinfo=None)
                except ValueError as e:
                    # If still failing, try a more aggressive approach
                    logger.warning(f"First parsing attempt failed: {e}")
                    
                    # Extract just the date and time part before any timezone
                    # This handles cases where the format is still incorrect
                    if 'T' in timestamp_str:
                        date_part, time_part = timestamp_str.split('T')
                        time_part = time_part.split('+')[0].split('-')[0].split('Z')[0].split('.')[0]
                        simple_timestamp = f"{date_part}T{time_part}"
                        
                        try:
                            return datetime.fromisoformat(simple_timestamp)
                        except ValueError:
                            # Last resort fallback
                            logger.warning(f"Even simplified timestamp parsing failed for: {timestamp_str}")
                            return datetime.now()
                    else:
                        return datetime.now()
            
            # Not a string or datetime
            return datetime.now()
            
        except Exception as e:
            logger.warning(f"Unable to parse timestamp: {timestamp_str}, using current time. Error: {e}")
            return datetime.now()
    
    def _ensure_naive_datetime(self, dt_value):
        """Convert any datetime value to a naive datetime.
        
        Args:
            dt_value: A datetime object, ISO string or None
            
        Returns:
            datetime: A naive datetime object
        """
        # Handle None case
        if dt_value is None:
            return datetime.now()
        
        # Use our parsing function to handle all cases consistently
        return self._safe_parse_timestamp(dt_value)
        
    def format_iso_datetime(self, dt_value):
        """Format a datetime as ISO 8601 string without timezone.
        
        Args:
            dt_value: A datetime object or None
            
        Returns:
            str: ISO 8601 formatted datetime string
        """
        # Ensure we have a naive datetime
        dt = self._ensure_naive_datetime(dt_value)
        
        # Format to ISO 8601 without timezone info
        return dt.isoformat() 