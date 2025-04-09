import os
from supabase import create_client, Client
from datetime import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import json

load_dotenv(override=True)

class DatabaseManager:
    def __init__(self):
        url: str = os.getenv("SUPABASE_URL")
        key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self.supabase: Client = create_client(url, key)

    def create_conversation(self, user_id: str) -> int:
        response = self.supabase.table('conversations').insert({
            'user_id': user_id
        }).execute()
        return response.data[0]['id']

    def add_message(self, session_id: str, role: str, message: str, metadata: Optional[Dict[str, Any]] = None, embedding: Optional[List[float]] = None):
        """Enhanced add_message with metadata support"""
        self.supabase.table('messages').insert({
            'session_id': session_id,
            'role': role,
            'message': message,
            'metadata': json.dumps(metadata) if metadata else None,
            'embedding_nomic': embedding,
            'created_at': datetime.now().isoformat()
        }).execute()

    def get_recent_messages(self, session_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        response = self.supabase.table('messages')\
            .select('role, message')\
            .eq('session_id', session_id)\
            .order('created_at', desc=True)\
            .limit(limit)\
            .execute()
        return response.data

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
                'task_history': json.dumps(state.get('task_history', [])),
                'agent_states': json.dumps(state.get('agent_states', {})),
                'agent_results': json.dumps(state.get('agent_results', {})),
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
            'agent_states': json.dumps(agent_states),
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
        query = self.supabase.table('messages')\
            .select('*')\
            .eq('session_id', conversation_id)\
            .order('created_at', desc=True)

        if start_date:
            query = query.gte('created_at', start_date.isoformat())
        if end_date:
            query = query.lte('created_at', end_date.isoformat())
        if role:
            query = query.eq('role', role)

        response = query.limit(limit).execute()
        return response.data

    async def search_conversations(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search conversations using full-text search"""
        search_query = self.supabase.table('messages')\
            .select('*')\
            .textSearch('message', query)\
            .order('created_at', desc=True)

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
        query = self.supabase.table('messages')\
            .select('*')\
            .eq('session_id', conversation_id)\
            .eq('metadata->>agent', agent_id)\
            .order('created_at', desc=True)

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
        message_counts = self.supabase.table('messages')\
            .select('role, count(*)')\
            .eq('session_id', conversation_id)\
            .group('role')\
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