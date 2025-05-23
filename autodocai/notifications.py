"""
Notification service for AutoDoc AI.

This module handles sending notifications about workflow status via email.
"""

import logging
import aiohttp
from typing import Dict, Any, Optional

from autodocai.config import AppConfig

logger = logging.getLogger("autodocai.notifications")

class NotificationService:
    """Service for sending notifications about workflow status."""
    
    def __init__(self, config: AppConfig):
        """
        Initialize the notification service.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self._sendgrid_api_key = config.sendgrid_api_key
        self._from_email = config.sendgrid_from_email
        self._to_email = config.notification_email_to
        
    async def send_success_notification(self, repo_url: str, docs_path: str, stats: Dict[str, Any]) -> bool:
        """
        Send a success notification.
        
        Args:
            repo_url: Repository URL
            docs_path: Path to generated documentation
            stats: Statistics about the generated documentation
            
        Returns:
            bool: True if notification was sent successfully
        """
        if not self._can_send_notifications():
            logger.info("Email notifications not configured, skipping success notification")
            return False
            
        subject = f"AutoDoc AI: Documentation generated successfully for {repo_url.split('/')[-1]}"
        
        content = f"""
        <h2>Documentation Generated Successfully</h2>
        <p><strong>Repository:</strong> {repo_url}</p>
        <p><strong>Documentation Path:</strong> {docs_path}</p>
        
        <h3>Statistics</h3>
        <ul>
            <li>Files Processed: {stats.get('files_processed', 0)}</li>
            <li>Functions Documented: {stats.get('functions_documented', 0)}</li>
            <li>Classes Documented: {stats.get('classes_documented', 0)}</li>
            <li>Diagrams Generated: {stats.get('diagrams_generated', 0)}</li>
        </ul>
        """
        
        return await self._send_email(subject, content)
    
    async def send_error_notification(self, repo_url: str, error_message: str, stage: Optional[str] = None) -> bool:
        """
        Send an error notification.
        
        Args:
            repo_url: Repository URL
            error_message: Error message
            stage: Stage where the error occurred
            
        Returns:
            bool: True if notification was sent successfully
        """
        if not self._can_send_notifications():
            logger.info("Email notifications not configured, skipping error notification")
            return False
            
        subject = f"AutoDoc AI: Error processing {repo_url.split('/')[-1]}"
        
        content = f"""
        <h2>Error Processing Repository</h2>
        <p><strong>Repository:</strong> {repo_url}</p>
        <p><strong>Stage:</strong> {stage or 'Unknown'}</p>
        
        <h3>Error Details</h3>
        <pre>{error_message}</pre>
        """
        
        return await self._send_email(subject, content)
    
    def _can_send_notifications(self) -> bool:
        """
        Check if notifications can be sent.
        
        Returns:
            bool: True if all required configuration is present
        """
        return (
            self._sendgrid_api_key and 
            self._from_email and 
            self._to_email
        )
    
    async def _send_email(self, subject: str, html_content: str) -> bool:
        """
        Send an email using SendGrid API.
        
        Args:
            subject: Email subject
            html_content: HTML content of the email
            
        Returns:
            bool: True if email was sent successfully
        """
        if not self._can_send_notifications():
            return False
            
        try:
            url = "https://api.sendgrid.com/v3/mail/send"
            headers = {
                "Authorization": f"Bearer {self._sendgrid_api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "personalizations": [
                    {
                        "to": [{"email": self._to_email}],
                        "subject": subject
                    }
                ],
                "from": {"email": self._from_email},
                "content": [
                    {
                        "type": "text/html",
                        "value": html_content
                    }
                ]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 202:
                        logger.info(f"Email notification sent successfully: {subject}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to send email notification: {response.status} - {error_text}")
                        return False
                        
        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}")
            return False
