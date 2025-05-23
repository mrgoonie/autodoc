"""
GitHub repository manager for AutoDoc AI.

This module handles GitHub repository access, cloning, and metadata extraction.
"""

import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import git
from git import Repo

from autodocai.schemas import RepositoryInfo


class GitHubRepoManager:
    """Manager for GitHub repository operations.
    
    This class handles cloning GitHub repositories and extracting metadata
    about the repository for further processing.
    """
    
    def __init__(
        self, 
        repo_url: str, 
        github_pat: Optional[str] = None, 
        git_executable: Optional[str] = None,
        work_dir: Optional[str] = None
    ):
        """Initialize the GitHub repository manager.
        
        Args:
            repo_url: URL of the GitHub repository
            github_pat: GitHub Personal Access Token for private repositories
            git_executable: Path to git executable (if not in PATH)
            work_dir: Directory to clone repositories into (uses temp dir if None)
        """
        self.repo_url = repo_url
        self.github_pat = github_pat
        self.git_executable = git_executable
        
        # Create a secure URL with PAT if provided
        if github_pat and "https://" in repo_url:
            # Format: https://TOKEN@github.com/username/repo.git
            self.clone_url = repo_url.replace(
                "https://", f"https://{github_pat}@"
            )
        else:
            self.clone_url = repo_url
            
        # Set up working directory
        self.work_dir = work_dir or tempfile.mkdtemp(prefix="autodocai_")
        self.repo_path = None
        self.repo = None
    
    async def clone(self) -> RepositoryInfo:
        """Clone the repository and return information about it.
        
        Returns:
            RepositoryInfo: Information about the cloned repository
            
        Raises:
            ValueError: If repository URL is invalid
            git.GitCommandError: If cloning fails
        """
        # Extract repo name from URL
        repo_name = self._extract_repo_name()
        if not repo_name:
            raise ValueError(f"Invalid GitHub repository URL: {self.repo_url}")
        
        # Set up repo path
        self.repo_path = os.path.join(self.work_dir, repo_name)
        
        # Clone the repository
        try:
            # Clean up directory if it exists
            if os.path.exists(self.repo_path):
                shutil.rmtree(self.repo_path)
            
            # Clone repository
            env = os.environ.copy()
            if self.git_executable:
                env["GIT_EXECUTABLE"] = self.git_executable
                
            self.repo = Repo.clone_from(
                self.clone_url, 
                self.repo_path,
                env=env
            )
            
            # Get repository info
            info = self._get_repo_info()
            return info
            
        except git.GitCommandError as e:
            if "Authentication failed" in str(e):
                raise ValueError(
                    "Authentication failed. If this is a private repository, "
                    "please provide a valid GitHub Personal Access Token."
                ) from e
            else:
                raise
    
    def cleanup(self):
        """Clean up temporary directories."""
        if self.repo_path and os.path.exists(self.repo_path):
            try:
                shutil.rmtree(self.repo_path)
            except Exception:
                pass
    
    def _extract_repo_name(self) -> str:
        """Extract repository name from URL.
        
        Returns:
            str: Repository name
        """
        # Match patterns like:
        # https://github.com/username/repo.git
        # https://github.com/username/repo
        # git@github.com:username/repo.git
        patterns = [
            r"github\.com[/:]([^/]+)/([^/.]+)(?:\.git)?$",
            r"github\.com[/:]([^/]+)/([^/.]+)/?$"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.repo_url)
            if match:
                username, repo = match.groups()
                return f"{username}_{repo}"
        
        return ""
    
    def _get_repo_info(self) -> RepositoryInfo:
        """Get information about the repository.
        
        Returns:
            RepositoryInfo: Information about the repository
        """
        # Get default branch
        default_branch = self.repo.active_branch.name
        
        # Determine if repo is private
        is_private = False
        if self.github_pat:
            # A crude way to check if repo is private - we needed a token to access it
            is_private = True
        
        # Determine languages (based on file extensions)
        languages = self._detect_languages()
        
        # Get description from README if available
        description = self._extract_description()
        
        # Create repository info
        return RepositoryInfo(
            name=os.path.basename(self.repo_path),
            url=self.repo_url,
            local_path=self.repo_path,
            default_branch=default_branch,
            languages=languages,
            description=description,
            is_private=is_private
        )
    
    def _detect_languages(self) -> List[str]:
        """Detect programming languages in the repository.
        
        Returns:
            List[str]: List of programming languages
        """
        extension_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".jsx": "JavaScript",
            ".tsx": "TypeScript",
            ".java": "Java",
            ".c": "C",
            ".cpp": "C++",
            ".cs": "C#",
            ".go": "Go",
            ".rb": "Ruby",
            ".php": "PHP",
            ".swift": "Swift",
            ".kt": "Kotlin",
            ".rs": "Rust",
        }
        
        language_count: Dict[str, int] = {}
        
        # Walk through repository and count file extensions
        for root, _, files in os.walk(self.repo_path):
            # Skip .git directory
            if ".git" in root:
                continue
                
            for file in files:
                _, ext = os.path.splitext(file)
                if ext in extension_map:
                    lang = extension_map[ext]
                    language_count[lang] = language_count.get(lang, 0) + 1
        
        # Sort by count in descending order and return languages
        sorted_langs = sorted(language_count.items(), key=lambda x: x[1], reverse=True)
        return [lang for lang, _ in sorted_langs]
    
    def _extract_description(self) -> Optional[str]:
        """Extract description from README file.
        
        Returns:
            Optional[str]: Repository description from README
        """
        readme_patterns = [
            "README.md",
            "Readme.md",
            "readme.md",
            "README.txt",
            "README",
        ]
        
        for pattern in readme_patterns:
            readme_path = os.path.join(self.repo_path, pattern)
            if os.path.exists(readme_path):
                try:
                    with open(readme_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        
                    # Extract first paragraph as description
                    lines = content.split("\n")
                    description_lines = []
                    
                    # Skip title lines (starting with #)
                    start_idx = 0
                    while start_idx < len(lines) and (not lines[start_idx].strip() or lines[start_idx].strip().startswith("#")):
                        start_idx += 1
                    
                    # Get first paragraph
                    for i in range(start_idx, len(lines)):
                        line = lines[i].strip()
                        if not line:
                            break
                        description_lines.append(line)
                    
                    if description_lines:
                        return " ".join(description_lines)[:500]  # Limit to 500 chars
                        
                except Exception:
                    pass
        
        return None


async def clone_repository(
    repo_url: str, 
    github_pat: Optional[str] = None,
    git_executable: Optional[str] = None,
    work_dir: Optional[str] = None
) -> RepositoryInfo:
    """Clone a GitHub repository and return information about it.
    
    Args:
        repo_url: URL of the GitHub repository
        github_pat: GitHub Personal Access Token for private repositories
        git_executable: Path to git executable (if not in PATH)
        work_dir: Directory to clone repositories into
        
    Returns:
        RepositoryInfo: Information about the cloned repository
        
    Raises:
        ValueError: If repository URL is invalid
        git.GitCommandError: If cloning fails
    """
    manager = GitHubRepoManager(repo_url, github_pat, git_executable, work_dir)
    return await manager.clone()


def get_repo_info(repo_path: str) -> RepositoryInfo:
    """Get information about a local repository.
    
    Args:
        repo_path: Path to local repository
        
    Returns:
        RepositoryInfo: Information about the repository
        
    Raises:
        ValueError: If path is not a valid git repository
    """
    try:
        repo = Repo(repo_path)
        
        # Get remote URL (origin)
        try:
            remote_url = repo.remotes.origin.url
        except (AttributeError, ValueError):
            remote_url = "Unknown"
        
        # Get default branch
        try:
            default_branch = repo.active_branch.name
        except (TypeError, ValueError):
            default_branch = "main"  # Default to main if can't determine
        
        # Determine languages
        extension_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".jsx": "JavaScript",
            ".tsx": "TypeScript",
            ".java": "Java",
            ".c": "C",
            ".cpp": "C++",
            ".cs": "C#",
            ".go": "Go",
            ".rb": "Ruby",
            ".php": "PHP",
            ".swift": "Swift",
            ".kt": "Kotlin",
            ".rs": "Rust",
        }
        
        language_count: Dict[str, int] = {}
        
        # Walk through repository and count file extensions
        for root, _, files in os.walk(repo_path):
            # Skip .git directory
            if ".git" in root:
                continue
                
            for file in files:
                _, ext = os.path.splitext(file)
                if ext in extension_map:
                    lang = extension_map[ext]
                    language_count[lang] = language_count.get(lang, 0) + 1
        
        # Sort by count in descending order
        sorted_langs = sorted(language_count.items(), key=lambda x: x[1], reverse=True)
        languages = [lang for lang, _ in sorted_langs]
        
        # Get description from README
        description = None
        readme_patterns = ["README.md", "Readme.md", "readme.md", "README.txt", "README"]
        
        for pattern in readme_patterns:
            readme_path = os.path.join(repo_path, pattern)
            if os.path.exists(readme_path):
                try:
                    with open(readme_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        
                    # Extract first paragraph as description
                    lines = content.split("\n")
                    description_lines = []
                    
                    # Skip title lines (starting with #)
                    start_idx = 0
                    while start_idx < len(lines) and (not lines[start_idx].strip() or lines[start_idx].strip().startswith("#")):
                        start_idx += 1
                    
                    # Get first paragraph
                    for i in range(start_idx, len(lines)):
                        line = lines[i].strip()
                        if not line:
                            break
                        description_lines.append(line)
                    
                    if description_lines:
                        description = " ".join(description_lines)[:500]  # Limit to 500 chars
                        break
                        
                except Exception:
                    pass
        
        # Create repository info
        return RepositoryInfo(
            name=os.path.basename(repo_path),
            url=remote_url,
            local_path=repo_path,
            default_branch=default_branch,
            languages=languages,
            description=description,
            is_private=False  # Assume local repos are not private
        )
        
    except git.InvalidGitRepositoryError:
        raise ValueError(f"The path '{repo_path}' is not a valid git repository.")
