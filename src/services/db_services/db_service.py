import logging
from src.services.db_services.db_manager import DatabaseManager, TaskStatus, StateTransitionError

class DBService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        try:
            self.db = DatabaseManager()
            self.has_db = True
            self.logger.debug("Database initialized successfully")
        except Exception as e:
            error_msg = f"Database initialization failed: {e}"
            self.logger.error(error_msg)
            print(error_msg)
            self.has_db = False

    def update_task_status(self, conversation_state, new_status: TaskStatus) -> bool:
        """Update the task status of the current conversation."""
        if not self.has_db or not conversation_state:
            return False
        
        try:
            result = self.db.update_task_status(conversation_state, new_status)
            if result:
                self.logger.debug(f"Updated task status to {new_status}")
                return True
            else:
                self.logger.error(f"Failed to update task status to {new_status}")
                return False
        except StateTransitionError as e:
            error_msg = f"Invalid task status transition: {e}"
            self.logger.error(error_msg)
            return False
        except Exception as e:
            error_msg = f"Error updating task status: {e}"
            self.logger.error(error_msg)
            return False 