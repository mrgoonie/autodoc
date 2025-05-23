"""
Configuration module for AutoDoc AI.

This module handles loading and validating configuration from environment variables and CLI arguments.
"""

import os
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

import click


class LogLevel(str, Enum):
    """Log levels for the application."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass
class AppConfig:
    """Application configuration for AutoDoc AI."""
    
    # Required settings
    target_repo_url: str
    output_dir: str
    openrouter_api_key: str
    qdrant_url: str
    
    # Optional settings with defaults
    github_pat: Optional[str] = None
    output_languages: List[str] = None
    log_level: LogLevel = LogLevel.INFO
    
    # AI model settings
    embedding_model_name: str = "openai/text-embedding-3-small"
    summarizer_model_name: str = "anthropic/claude-3-haiku"
    translation_model_name: str = "google/gemini-pro"
    rag_model_name: str = "anthropic/claude-3-haiku"
    
    # Email notification settings
    sendgrid_api_key: Optional[str] = None
    sendgrid_from_email: Optional[str] = None
    notification_email_to: Optional[str] = None
    
    # Advanced settings
    git_executable_path: Optional[str] = None
    debug: bool = False
    
    @classmethod
    def from_env_and_args(
        cls,
        repo_url: Optional[str] = None,
        output_dir: Optional[str] = None,
        languages: Optional[str] = None,
        github_pat: Optional[str] = None,
        debug: bool = False,
    ) -> "AppConfig":
        """Create configuration from environment variables and CLI arguments.
        
        CLI arguments take precedence over environment variables.
        
        Args:
            repo_url: GitHub repository URL
            output_dir: Directory for generated documentation
            languages: Comma-separated languages
            github_pat: GitHub Personal Access Token
            debug: Enable debug mode
            
        Returns:
            AppConfig: Application configuration
        """
        # Get values from environment variables
        env_repo_url = os.getenv("TARGET_REPO_URL")
        env_output_dir = os.getenv("OUTPUT_DIR")
        env_languages = os.getenv("OUTPUT_LANGUAGES", "EN,VI")
        env_github_pat = os.getenv("GITHUB_PAT")
        env_log_level = os.getenv("LOG_LEVEL", LogLevel.INFO.value)
        
        # Get API keys and service URLs
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        
        # Email notification settings
        sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
        sendgrid_from_email = os.getenv("SENDGRID_FROM_EMAIL")
        notification_email_to = os.getenv("NOTIFICATION_EMAIL_TO")
        
        # AI model settings
        embedding_model = os.getenv("EMBEDDING_MODEL_NAME", "openai/text-embedding-3-small")
        summarizer_model = os.getenv("SUMMARIZER_MODEL_NAME", "anthropic/claude-3-haiku")
        translation_model = os.getenv("TRANSLATION_MODEL_NAME", "google/gemini-pro")
        rag_model = os.getenv("RAG_MODEL_NAME", "anthropic/claude-3-haiku")
        
        # Advanced settings
        git_executable = os.getenv("GIT_EXECUTABLE_PATH")
        
        # CLI args override env vars
        final_repo_url = repo_url or env_repo_url
        final_output_dir = output_dir or env_output_dir
        final_languages = languages or env_languages
        final_github_pat = github_pat or env_github_pat
        
        # Parse language list
        language_list = [lang.strip() for lang in final_languages.split(",") if lang.strip()] if final_languages else ["EN"]
        
        # Create configuration
        config = cls(
            target_repo_url=final_repo_url,
            output_dir=final_output_dir,
            openrouter_api_key=openrouter_api_key,
            qdrant_url=qdrant_url,
            github_pat=final_github_pat,
            output_languages=language_list,
            log_level=LogLevel(env_log_level),
            embedding_model_name=embedding_model,
            summarizer_model_name=summarizer_model,
            translation_model_name=translation_model,
            rag_model_name=rag_model,
            sendgrid_api_key=sendgrid_api_key,
            sendgrid_from_email=sendgrid_from_email,
            notification_email_to=notification_email_to,
            git_executable_path=git_executable,
            debug=debug,
        )
        
        return config
    
    def validate(self) -> bool:
        """Validate the configuration.
        
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        # Check required fields
        missing = []
        
        if not self.target_repo_url:
            missing.append("Repository URL (TARGET_REPO_URL)")
        
        if not self.output_dir:
            missing.append("Output directory (OUTPUT_DIR)")
        
        if not self.openrouter_api_key:
            missing.append("OpenRouter API key (OPENROUTER_API_KEY)")
        
        if not self.qdrant_url:
            missing.append("Qdrant URL (QDRANT_URL)")
        
        # Report missing values
        if missing:
            click.echo("❌ Missing required configuration:")
            for field in missing:
                click.echo(f"   - {field}")
            return False
        
        # Enable debug mode if requested
        if self.debug and self.log_level != LogLevel.DEBUG:
            self.log_level = LogLevel.DEBUG
            click.echo("🔍 Debug mode enabled")
        
        # Check if languages are valid
        for lang in self.output_languages:
            if lang not in ["EN", "VI"]:
                click.echo(f"⚠️ Warning: Unsupported language '{lang}'. Currently only EN and VI are supported.")
                self.output_languages = [l for l in self.output_languages if l in ["EN", "VI"]]
        
        if not self.output_languages:
            click.echo("⚠️ No valid languages specified. Defaulting to English (EN).")
            self.output_languages = ["EN"]
        
        # Check notification configuration
        if any([self.sendgrid_api_key, self.sendgrid_from_email, self.notification_email_to]):
            missing_notification = []
            
            if not self.sendgrid_api_key:
                missing_notification.append("SendGrid API key (SENDGRID_API_KEY)")
            
            if not self.sendgrid_from_email:
                missing_notification.append("SendGrid from email (SENDGRID_FROM_EMAIL)")
            
            if not self.notification_email_to:
                missing_notification.append("Notification recipient email (NOTIFICATION_EMAIL_TO)")
            
            if missing_notification:
                click.echo("⚠️ Incomplete notification configuration. Email notifications will be disabled:")
                for field in missing_notification:
                    click.echo(f"   - Missing {field}")
                
                # Disable notifications if configuration is incomplete
                self.sendgrid_api_key = None
                self.sendgrid_from_email = None
                self.notification_email_to = None
        
        return True
