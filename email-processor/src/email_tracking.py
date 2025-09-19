"""
Email tracking module for preventing duplicate processing.
"""
import os
import json
from typing import Set
from loguru import logger
from datetime import datetime


class EmailTracker:
    """Tracks processed emails to prevent duplicate processing."""
    
    def __init__(self, tracking_file: str = "/app/logs/processed_emails.json"):
        self.tracking_file = tracking_file
        self.processed_emails = self._load_processed_emails()
    
    def _load_processed_emails(self) -> Set[int]:
        """Load list of processed email IDs from file."""
        try:
            if os.path.exists(self.tracking_file):
                with open(self.tracking_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return set(data.get('processed_email_ids', []))
            return set()
        except Exception as e:
            logger.warning(f"Error loading processed emails: {e}")
            return set()
    
    def _save_processed_emails(self):
        """Save list of processed email IDs to file."""
        try:
            os.makedirs(os.path.dirname(self.tracking_file), exist_ok=True)
            data = {
                'processed_email_ids': list(self.processed_emails),
                'last_updated': datetime.now().isoformat()
            }
            with open(self.tracking_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving processed emails: {e}")
    
    def is_processed(self, email_id: int) -> bool:
        """Check if email was already processed."""
        return email_id in self.processed_emails
    
    def mark_as_processed(self, email_id: int):
        """Mark email as processed."""
        self.processed_emails.add(email_id)
        self._save_processed_emails()
        logger.info(f"Marked email {email_id} as processed")
    
    def cleanup_old_entries(self, keep_last_n: int = 1000):
        """Keep only the last N processed emails to prevent file from growing too large."""
        if len(self.processed_emails) > keep_last_n:
            # Keep the most recent entries (highest IDs)
            self.processed_emails = set(sorted(self.processed_emails)[-keep_last_n:])
            self._save_processed_emails()
            logger.info(f"Cleaned up old processed emails, keeping {keep_last_n} most recent")
