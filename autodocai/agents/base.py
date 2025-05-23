"""
Base agent class for AutoDoc AI.

This module defines the base agent class that all other agents inherit from,
providing common functionality and a consistent interface.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from autodocai.config import AppConfig
from autodocai.schemas import AgentMessage, MessageType


class BaseAgent(ABC):
    """Base class for all agents in AutoDoc AI.
    
    This abstract class provides common functionality for all agents, such as
    logging, message handling, and a consistent interface for execution.
    """
    
    def __init__(self, config: AppConfig):
        """Initialize the base agent.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.logger = logging.getLogger(f"autodocai.agents.{self.__class__.__name__}")
    
    def get_state_value(self, state: Union[Dict[str, Any], BaseModel], key: str, default: Any = None) -> Any:
        """Get a value from the state, handling both dictionary and Pydantic model states.
        
        Args:
            state: Current workflow state (either a dictionary or a Pydantic model)
            key: Key to get from the state
            default: Default value to return if key is not found
            
        Returns:
            Any: Value from the state, or default if not found
        """
        if isinstance(state, dict):
            return state.get(key, default)
        elif hasattr(state, key):
            value = getattr(state, key)
            return value if value is not None else default
        return default
    
    def set_state_value(self, state: Union[Dict[str, Any], BaseModel], key: str, value: Any) -> None:
        """Set a value in the state, handling both dictionary and Pydantic model states.
        
        Args:
            state: Current workflow state (either a dictionary or a Pydantic model)
            key: Key to set in the state
            value: Value to set
        """
        if isinstance(state, dict):
            state[key] = value
        elif hasattr(state, key):
            setattr(state, key, value)
    
    @property
    def name(self) -> str:
        """Get the agent's name.
        
        Returns:
            str: The agent's name
        """
        return self.__class__.__name__
    
    @abstractmethod
    async def _execute(self, state: Union[Dict[str, Any], BaseModel]) -> Union[Dict[str, Any], BaseModel]:
        """Execute the agent's task.
        
        This is the main method that each agent must implement to perform its specific task.
        
        Args:
            state: Current workflow state (either a dictionary or a Pydantic model)
            
        Returns:
            Union[Dict[str, Any], BaseModel]: Updated workflow state
        """
        pass
    
    async def execute(self, state: Union[Dict[str, Any], BaseModel]) -> Union[Dict[str, Any], BaseModel]:
        """Execute the agent's task with logging and error handling.
        
        This method wraps the _execute method with common functionality like
        logging and error handling.
        
        Args:
            state: Current workflow state (either a dictionary or a Pydantic model)
            
        Returns:
            Union[Dict[str, Any], BaseModel]: Updated workflow state
        """
        try:
            self.logger.info(f"Starting execution")
            
            # Add a message to the state
            self._add_message(state, MessageType.INFO, f"{self.name} started processing")
            
            # Execute the agent's task
            updated_state = await self._execute(state)
            
            # Add a success message
            self._add_message(updated_state, MessageType.SUCCESS, f"{self.name} completed successfully")
            
            self.logger.info(f"Completed execution")
            return updated_state
            
        except Exception as e:
            self.logger.error(f"Error during execution: {str(e)}", exc_info=True)
            
            # Add error message and error to the state
            self._add_message(state, MessageType.ERROR, f"Error in {self.name}: {str(e)}")
            
            # Add error to the errors list
            if isinstance(state, dict):
                if "errors" not in state:
                    state["errors"] = []
                state["errors"].append({"agent": self.name, "message": str(e)})
            elif hasattr(state, "errors"):
                # If it's a Pydantic model, we need to append to the list in a different way
                if state.errors is None:
                    state.errors = []
                state.errors.append({"agent": self.name, "message": str(e)})
            
            return state
    
    def _add_message(
        self, state: Union[Dict[str, Any], BaseModel], message_type: MessageType, content: str
    ) -> None:
        """Add a message to the state.
        
        Args:
            state: Current workflow state (either a dictionary or a Pydantic model)
            message_type: Type of message
            content: Message content
        """
        # Create the message
        message = AgentMessage(
            agent_name=self.name,
            message_type=message_type,
            content=content,
            timestamp=datetime.now().isoformat(),
        )
        
        # Add the message to the state
        if isinstance(state, dict):
            # Dictionary-style state
            if "messages" not in state:
                state["messages"] = []
            state["messages"].append(message)
        elif hasattr(state, "messages"):
            # Pydantic model state
            if state.messages is None:
                state.messages = []
            state.messages.append(message)
