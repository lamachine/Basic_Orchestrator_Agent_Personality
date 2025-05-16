"""
Template Agent State Validator.

This module provides state validation for the template agent,
inheriting core validation from the orchestrator but adding
template-specific validation rules.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import ValidationError
from src.state.state_validator import StateValidator as BaseStateValidator
from .state_models import (
    TemplateMessage,
    TemplateStateUpdate,
    TemplateStateSnapshot,
    TemplateState,
    TemplateMessageType,
    TemplateMessageStatus
)
from ..services.logging_service import get_logger

logger = get_logger(__name__)

class StateValidator(BaseStateValidator):
    """
    Template agent state validator.
    
    This validator extends the base state validator with template-specific
    validation rules and error handling.
    """
    
    def __init__(self):
        """Initialize the template state validator."""
        super().__init__()
        self.source_prefix = "template"
        logger.debug("Initialized template state validator")
    
    def validate_message(
        self,
        message: Dict[str, Any]
    ) -> TemplateMessage:
        """
        Validate a message with template-specific rules.
        
        Args:
            message: The message to validate
            
        Returns:
            TemplateMessage: The validated message
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            # Add template-specific validation
            if "template_type" not in message:
                message["template_type"] = TemplateMessageType.TOOL_REQUEST
            if "template_status" not in message:
                message["template_status"] = TemplateMessageStatus.PENDING
            if "template_metadata" not in message:
                message["template_metadata"] = {}
            
            # Validate using base validator
            validated = super().validate_message(message)
            
            # Convert to template message
            return TemplateMessage(**validated.dict())
            
        except ValidationError as e:
            logger.error(f"Message validation failed: {str(e)}")
            raise
    
    def validate_state_update(
        self,
        update: Dict[str, Any]
    ) -> TemplateStateUpdate:
        """
        Validate a state update with template-specific rules.
        
        Args:
            update: The state update to validate
            
        Returns:
            TemplateStateUpdate: The validated state update
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            # Add template-specific validation
            if "template_updates" not in update:
                update["template_updates"] = {}
            if "template_metadata" not in update:
                update["template_metadata"] = {}
            
            # Validate using base validator
            validated = super().validate_state_update(update)
            
            # Convert to template state update
            return TemplateStateUpdate(**validated.dict())
            
        except ValidationError as e:
            logger.error(f"State update validation failed: {str(e)}")
            raise
    
    def validate_state_snapshot(
        self,
        snapshot: Dict[str, Any]
    ) -> TemplateStateSnapshot:
        """
        Validate a state snapshot with template-specific rules.
        
        Args:
            snapshot: The state snapshot to validate
            
        Returns:
            TemplateStateSnapshot: The validated state snapshot
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            # Add template-specific validation
            if "template_state" not in snapshot:
                snapshot["template_state"] = {}
            if "template_metadata" not in snapshot:
                snapshot["template_metadata"] = {}
            
            # Validate using base validator
            validated = super().validate_state_snapshot(snapshot)
            
            # Convert to template state snapshot
            return TemplateStateSnapshot(**validated.dict())
            
        except ValidationError as e:
            logger.error(f"State snapshot validation failed: {str(e)}")
            raise
    
    def validate_state(
        self,
        state: Dict[str, Any]
    ) -> TemplateState:
        """
        Validate a state with template-specific rules.
        
        Args:
            state: The state to validate
            
        Returns:
            TemplateState: The validated state
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            # Add template-specific validation
            if "parent_state" not in state:
                state["parent_state"] = {}
            if "template_state" not in state:
                state["template_state"] = {}
            if "metadata" not in state:
                state["metadata"] = {}
            
            # Validate using template state model
            return TemplateState(**state)
            
        except ValidationError as e:
            logger.error(f"State validation failed: {str(e)}")
            raise 