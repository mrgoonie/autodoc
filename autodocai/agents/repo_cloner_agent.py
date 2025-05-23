"""
Repository cloner agent for AutoDoc AI.

This agent is responsible for cloning GitHub repositories and preparing them for code analysis.
"""

import logging
import os
from typing import Any, Dict

from autodocai.config import AppConfig
from autodocai.agents.base import BaseAgent
from autodocai.repo_manager import clone_repository
from autodocai.schemas import MessageType


class RepoClonerAgent(BaseAgent):
    """Agent for cloning GitHub repositories.
    
    This agent handles the process of cloning a GitHub repository using the specified URL
    and GitHub Personal Access Token (if provided for private repositories).
    """
    
    async def _execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the repository cloning process.
        
        Args:
            state: Current workflow state
            
        Returns:
            Dict[str, Any]: Updated workflow state with repository information
        """
        config = state["config"]
        
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
            
            # Add repository information to state
            state["repo_info"] = repo_info
            
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
