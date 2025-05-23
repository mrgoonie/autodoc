"""
Repository management module for AutoDoc AI.

This package handles GitHub repository access, cloning, and basic information retrieval.
"""

from autodocai.repo_manager.github_repo import GitHubRepoManager, clone_repository, get_repo_info

__all__ = ["GitHubRepoManager", "clone_repository", "get_repo_info"]
