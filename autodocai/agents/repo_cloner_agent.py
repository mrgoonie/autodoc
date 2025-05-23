"""
Repository cloner agent for AutoDoc AI.

This agent is responsible for cloning GitHub repositories and preparing them for code analysis.
"""

import logging
import os
from typing import Any, Dict, Union

from pydantic import BaseModel

from autodocai.config import AppConfig
from autodocai.agents.base import BaseAgent
from autodocai.repo_manager import clone_repository
from autodocai.schemas import MessageType


class RepoClonerAgent(BaseAgent):
    """Agent for cloning GitHub repositories.
    
    This agent handles the process of cloning a GitHub repository using the specified URL
    and GitHub Personal Access Token (if provided for private repositories).
    """
    
    async def _execute(self, state: Union[Dict[str, Any], BaseModel]) -> Union[Dict[str, Any], BaseModel]:
        """Execute the repository cloning process.
        
        Args:
            state: Current workflow state (dictionary or Pydantic model)
            
        Returns:
            Union[Dict[str, Any], BaseModel]: Updated workflow state with repository information
        """
        # Get the config - for Pydantic models, we just use the config attribute directly
        if hasattr(state, "config") and state.config:
            config = state.config
        elif hasattr(state, "repo_url") and hasattr(state, "output_dir"):
            # If this is a WorkflowState without config (LangGraph model)
            # use the properties directly from the state
            config = self.config
            repo_url = self.get_state_value(state, "repo_url")
            output_dir = self.get_state_value(state, "output_dir")
            if repo_url:
                config.target_repo_url = repo_url
            if output_dir:
                config.output_dir = output_dir
        else:
            # Try dictionary style
            config = self.get_state_value(state, "config", self.config)
        
        # Extract repository URL from configuration
        repo_url = config.target_repo_url
        
        if not repo_url:
            raise ValueError("Repository URL is required")
        
        self.logger.info(f"Cloning repository: {repo_url}")
        self._add_message(state, MessageType.INFO, f"Cloning repository: {repo_url}")
        
        try:
            # Clone the repository
            repo_info = await clone_repository(
                repo_url=repo_url,
                github_pat=config.github_pat,
                git_executable=config.git_executable_path,
                work_dir=os.path.join(os.path.dirname(config.output_dir), "repos")
            )
            
            # Add repository information to state using our helper method
            self.set_state_value(state, "repo_info", repo_info)
            
            # Update current stage in the state
            self.set_state_value(state, "current_stage", "repo_cloning_complete")
            
            self.logger.info(f"Repository cloned successfully: {repo_info.local_path}")
            self._add_message(
                state, 
                MessageType.SUCCESS, 
                f"Repository cloned successfully. Main languages: {', '.join(repo_info.languages)}"
            )
            
            return state
            
        except Exception as e:
            error_msg = f"Failed to clone repository: {str(e)}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
