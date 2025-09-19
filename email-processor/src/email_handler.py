"""
Email handler module for processing incoming emails with download links.
"""
import imaplib
import email
import re
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import decode_header
from bs4 import BeautifulSoup
from loguru import logger
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.config import config
from email_tracking import EmailTracker


class EmailHandler:
    """Handles email operations including fetching and parsing emails."""
    
    def __init__(self):
        self.imap_server = None
        self.email_config = config.email
        self.email_tracker = EmailTracker()
        
    def connect(self) -> bool:
        """
        Connect to the IMAP server.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            if self.email_config.use_ssl:
                self.imap_server = imaplib.IMAP4_SSL(
                    self.email_config.imap_server, 
                    self.email_config.imap_port
                )
            else:
                self.imap_server = imaplib.IMAP4(
                    self.email_config.imap_server, 
                    self.email_config.imap_port
                )
            
            # Login
            self.imap_server.login(
                self.email_config.email, 
                self.email_config.password
            )
            
            # Select mailbox
            self.imap_server.select(self.email_config.mailbox)
            logger.info(f"Successfully connected to {self.email_config.imap_server}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to email server: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the IMAP server."""
        if self.imap_server:
            try:
                self.imap_server.close()
                self.imap_server.logout()
                logger.info("Disconnected from email server")
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
    
    def search_emails(
        self, 
        criteria: str = "UNSEEN", 
        limit: int = 10
    ) -> List[int]:
        """
        Search for emails based on criteria.
        
        Args:
            criteria (str): IMAP search criteria (default: "UNSEEN" for unread emails)
            limit (int): Maximum number of emails to return
            
        Returns:
            List[int]: List of email UIDs
        """
        try:
            if not self.imap_server:
                raise Exception("Not connected to email server")
            
            # Search for emails
            status, messages = self.imap_server.search(None, criteria)
            
            if status != 'OK':
                logger.error("Failed to search emails")
                return []
            
            # Get email UIDs
            email_ids = messages[0].split()
            
            # Limit results
            if limit and len(email_ids) > limit:
                email_ids = email_ids[-limit:]
            
            # Convert to integers
            return [int(uid) for uid in email_ids]
            
        except Exception as e:
            logger.error(f"Error searching emails: {e}")
            return []
    
    def fetch_email(self, email_id: int) -> Optional[email.message.Message]:
        """
        Fetch a specific email by ID.
        
        Args:
            email_id (int): Email UID
            
        Returns:
            Optional[email.message.Message]: Email message object or None
        """
        try:
            if not self.imap_server:
                raise Exception("Not connected to email server")
            
            # Fetch email
            status, msg_data = self.imap_server.fetch(str(email_id), '(RFC822)')
            
            if status != 'OK':
                logger.error(f"Failed to fetch email {email_id}")
                return None
            
            # Parse email message
            email_body = msg_data[0][1]
            email_message = email.message_from_bytes(email_body)
            
            return email_message
            
        except Exception as e:
            logger.error(f"Error fetching email {email_id}: {e}")
            return None
    
    def extract_download_links(self, email_message: email.message.Message) -> List[str]:
        """
        Extract download links from email content.
        
        Args:
            email_message: Email message object
            
        Returns:
            List[str]: List of download URLs found in the email
        """
        download_links = []
        
        try:
            # Get email content
            content = self._get_email_content(email_message)
            
            if not content:
                return download_links
            
            # Parse HTML content with BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find all links
            links = soup.find_all('a', href=True)
            
            # Filter for download links (common patterns)
            download_patterns = [
                r'download',
                r'attachment',
                r'\.zip$',
                r'\.rar$',
                r'\.7z$',
                r'file\.php\?',
                r'download\.php\?',
                r'attachment\.php\?'
            ]
            
            for link in links:
                href = link['href']
                link_text = link.get_text().lower()
                
                # Check if link matches download patterns
                is_download_link = any(
                    re.search(pattern, href, re.IGNORECASE) or 
                    re.search(pattern, link_text, re.IGNORECASE)
                    for pattern in download_patterns
                )
                
                if is_download_link:
                    # Make sure it's a complete URL
                    if href.startswith('http'):
                        download_links.append(href)
                    
            logger.info(f"Found {len(download_links)} download links")
            return download_links
            
        except Exception as e:
            logger.error(f"Error extracting download links: {e}")
            return download_links
    
    def _get_email_content(self, email_message: email.message.Message) -> Optional[str]:
        """
        Extract content from email message.
        
        Args:
            email_message: Email message object
            
        Returns:
            Optional[str]: Email content (HTML preferred, plain text as fallback)
        """
        content = None
        
        try:
            if email_message.is_multipart():
                # Handle multipart emails
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition", ""))
                    
                    # Skip attachments
                    if "attachment" in content_disposition:
                        continue
                    
                    # Get text content
                    if content_type == "text/html":
                        content = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break  # Prefer HTML content
                    elif content_type == "text/plain" and not content:
                        content = part.get_payload(decode=True).decode('utf-8', errors='ignore')
            else:
                # Handle simple emails
                content = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
            
            return content
            
        except Exception as e:
            logger.error(f"Error extracting email content: {e}")
            return None
    
    def mark_as_read(self, email_id: int):
        """
        Mark email as read.
        
        Args:
            email_id (int): Email UID
        """
        try:
            if not self.imap_server:
                raise Exception("Not connected to email server")
            
            self.imap_server.store(str(email_id), '+FLAGS', '\\Seen')
            logger.debug(f"Marked email {email_id} as read")
            
        except Exception as e:
            logger.error(f"Error marking email as read: {e}")
    
    def get_latest_emails_with_downloads(self, limit: int = 5) -> List[Tuple[int, List[str]]]:
        """
        Get latest emails with subject 'Выписка по счету ООО "АДВАНТО"' 
        from today that contain download links and haven't been processed yet.
        
        Args:
            limit (int): Maximum number of emails to process
            
        Returns:
            List[Tuple[int, List[str]]]: List of tuples (email_id, download_links)
        """
        results = []
        
        try:
            # Get specific test date: 28.08.2025
            test_date = "29-Aug-2025 BEFORE 30-Aug-2025"
            
            # Search for all emails from test date (without Russian characters)
            search_criteria = f'SINCE {test_date}'
            email_ids = self.search_emails(search_criteria, limit * 10)  # Get more to filter by subject
            
            if not email_ids:
                logger.info(f"No emails found for test date ({test_date})")
                return results
            
            logger.info(f"Found {len(email_ids)} emails for test date {test_date}, filtering by subject...")


            
            # Filter emails by subject programmatically and cache messages
            target_subject = 'Выписка по счету ООО "АДВАНТО"'
            filtered_emails = []  # Store tuples of (email_id, email_message)
            
            for email_id in email_ids:
                try:
                    email_message = self.fetch_email(email_id)
                    if email_message:
                        subject = email_message.get('Subject', '')
                        # Decode subject if it's encoded
                        if subject:
                            try:
                                # Handle encoded subjects
                                decoded_parts = decode_header(subject)
                                subject = ''.join([
                                    part.decode(encoding or 'utf-8') if isinstance(part, bytes) else str(part)
                                    for part, encoding in decoded_parts
                                ])
                            except:
                                # If decoding fails, use as is
                                pass
                            
                            if target_subject in subject:
                                # ВРЕМЕННО ОТКЛЮЧЕНО ДЛЯ ТЕСТИРОВАНИЯ
                                # # Проверить, не было ли письмо уже обработано
                                # if self.email_tracker.is_processed(email_id):
                                #     logger.info(f"Email {email_id} already processed, skipping")
                                #     continue
                                
                                filtered_emails.append((email_id, email_message))
                                logger.info(f"Found matching email {email_id}: {subject}")
                except Exception as e:
                    logger.warning(f"Error checking email {email_id}: {e}")
                    continue
            
            if not filtered_emails:
                logger.info(f"No emails with subject '{target_subject}' found in the last 20 hours")
                return results
            
            logger.info(f"Found {len(filtered_emails)} emails with target subject")
            
            # Process each email (use cached messages)
            for email_id, email_message in filtered_emails[-limit:]:  # Get latest emails
                
                if not email_message:
                    continue
                
                # Extract download links
                download_links = self.extract_download_links(email_message)
                
                if download_links:
                    results.append((email_id, download_links))
                    logger.info(f"Email {email_id} contains {len(download_links)} download links")
                
                # Respect processing limit
                if len(results) >= limit:
                    break
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting emails with downloads: {e}")
            return results


# Context manager for easy email handling
class EmailContextManager:
    """Context manager for EmailHandler to ensure proper connection handling."""
    
    def __init__(self):
        self.handler = EmailHandler()
    
    def __enter__(self) -> EmailHandler:
        if not self.handler.connect():
            raise Exception("Failed to connect to email server")
        return self.handler
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.handler.disconnect()
