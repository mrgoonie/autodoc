"""
Notification utilities for AutoDoc AI.

This module provides email notification functionality using SendGrid.
"""

import os
import logging
from typing import Dict, List, Optional
from autodocai.config import AppConfig

logger = logging.getLogger("autodocai.notifications")

class NotificationService:
    """Service for sending notifications about documentation generation."""
    
    def __init__(self, config: AppConfig):
        """
        Initialize the notification service.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.enabled = bool(
            config.sendgrid_api_key and 
            config.sendgrid_from_email and 
            config.notification_email_to
        )
        
        if not self.enabled:
            logger.warning("SendGrid notifications are disabled due to missing configuration")
    
    async def send_success_notification(
        self, 
        repo_url: str, 
        docs_path: str, 
        stats: Dict[str, int]
    ) -> bool:
        """
        Send a success notification for documentation generation.
        
        Args:
            repo_url: URL of the repository
            docs_path: Path to the generated documentation
            stats: Statistics about the generated documentation
            
        Returns:
            bool: True if notification was sent successfully
        """
        if not self.enabled:
            logger.info("Skipping success notification - SendGrid not configured")
            return False
            
        subject = f"Documentation generated successfully for {repo_url}"
        
        content = f"""
        <h2>Documentation Generation Successful</h2>
        <p>AutoDoc AI has successfully generated documentation for repository: <strong>{repo_url}</strong></p>
        
        <h3>Statistics:</h3>
        <ul>
            <li>Files processed: {stats.get('files_processed', 0)}</li>
            <li>Functions documented: {stats.get('functions_documented', 0)}</li>
            <li>Classes documented: {stats.get('classes_documented', 0)}</li>
            <li>Diagrams generated: {stats.get('diagrams_generated', 0)}</li>
        </ul>
        
        <p>Documentation is available at: {docs_path}</p>
        
        <p>Thank you for using AutoDoc AI!</p>
        """
        
        return await self._send_email(subject, content)
    
    async def send_error_notification(
        self, 
        repo_url: str, 
        error_message: str, 
        stage: str
    ) -> bool:
        """
        Send an error notification.
        
        Args:
            repo_url: URL of the repository
            error_message: Error message
            stage: Stage where the error occurred
            
        Returns:
            bool: True if notification was sent successfully
        """
        if not self.enabled:
            logger.info("Skipping error notification - SendGrid not configured")
            return False
            
        subject = f"Documentation generation failed for {repo_url}"
        
        content = f"""
        <h2>Documentation Generation Failed</h2>
        <p>AutoDoc AI encountered an error while generating documentation for repository: <strong>{repo_url}</strong></p>
        
        <h3>Error Details:</h3>
        <p><strong>Stage:</strong> {stage}</p>
        <p><strong>Error Message:</strong></p>
        <pre>{error_message}</pre>
        
        <p>Please check the logs for more details.</p>
        """
        
        return await self._send_email(subject, content)
    
    async def _send_email(self, subject: str, html_content: str) -> bool:
        """
        Send an email using SendGrid API.
        
        Args:
            subject: Email subject
            html_content: HTML content of the email
            
        Returns:
            bool: True if email was sent successfully
        """
        try:
            # Import is done here to avoid dependency issues if SendGrid is not installed
            import sendgrid
            from sendgrid.helpers.mail import Mail, Email, To, Content
            
            sg = sendgrid.SendGridAPIClient(api_key=self.config.sendgrid_api_key)
            
            from_email = Email(self.config.sendgrid_from_email)
            to_email = To(self.config.notification_email_to)
            content = Content("text/html", html_content)
            
            mail = Mail(from_email, to_email, subject, content)
            response = sg.client.mail.send.post(request_body=mail.get())
            
            if response.status_code >= 200 and response.status_code < 300:
                logger.info(f"Email notification sent successfully, status code: {response.status_code}")
                return True
            else:
                logger.error(f"Failed to send email notification: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}")
            return False