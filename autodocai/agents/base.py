"""
Base agent class for AutoDoc AI.

This module defines the base agent class that all other agents inherit from,
providing common functionality and a consistent interface.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

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
    
    @property
    def name(self) -> str:
        """Get the agent's name.
        
        Returns:
            str: The agent's name
        """
        return self.__class__.__name__
    
    @abstractmethod
    async def _execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent's task.
        
        This is the main method that each agent must implement to perform its specific task.
        
        Args:
            state: Current workflow state
            
        Returns:
            Dict[str, Any]: Updated workflow state
        """
        pass
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent's task with logging and error handling.
        
        This method wraps the _execute method with common functionality like
        logging and error handling.
        
        Args:
            state: Current workflow state
            
        Returns:
            Dict[str, Any]: Updated workflow state
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
            
            if "errors" not in state:
                state["errors"] = []
            state["errors"].append(f"{self.name}: {str(e)}")
            
            return state
    
    def _add_message(
        self, state: Dict[str, Any], message_type: MessageType, content: str
    ) -> None:
        """Add a message to the state.
        
        Args:
            state: Current workflow state
            message_type: Type of message
            content: Message content
        """
        # Ensure messages list exists
        if "messages" not in state:
            state["messages"] = []
        
        # Create and add the message
        message = AgentMessage(
            agent_name=self.name,
            message_type=message_type,
            content=content,
            timestamp=datetime.now().isoformat(),
        )
        
        state["messages"].append(message)
