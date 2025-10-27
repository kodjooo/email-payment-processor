"""
Configuration settings for the email processor application.
"""
import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class EmailConfig:
    """Email server configuration."""
    imap_server: str = os.getenv('IMAP_SERVER', 'imap.gmail.com')
    imap_port: int = int(os.getenv('IMAP_PORT', '993'))
    email: str = os.getenv('EMAIL_ADDRESS', '')
    password: str = os.getenv('EMAIL_PASSWORD', '')
    mailbox: str = os.getenv('MAILBOX', 'INBOX')
    use_ssl: bool = os.getenv('USE_SSL', 'true').lower() == 'true'

@dataclass
class ProcessingConfig:
    """Data processing configuration."""
    download_folder: str = os.getenv('DOWNLOAD_FOLDER', './downloads')
    csv_filter_column: str = os.getenv('CSV_FILTER_COLUMN', 'status')
    csv_filter_value: str = os.getenv('CSV_FILTER_VALUE', 'completed')
    payment_amount_column: str = os.getenv('PAYMENT_AMOUNT_COLUMN', 'amount')
    payment_date_column: str = os.getenv('PAYMENT_DATE_COLUMN', 'date')
    payment_id_column: str = os.getenv('PAYMENT_ID_COLUMN', 'transaction_id')
    customer_id_column: str = os.getenv('CUSTOMER_ID_COLUMN', 'customer_id')

@dataclass
class WebhookConfig:
    """Webhook configuration."""
    webhook_url: str = os.getenv('WEBHOOK_URL', '')
    webhook_headers: dict = None
    webhook_timeout: int = int(os.getenv('WEBHOOK_TIMEOUT', '30'))
    token: str = os.getenv('WEBHOOK_TOKEN', '')
    basic_username: str = os.getenv('WEBHOOK_BASIC_USERNAME', '')
    basic_password: str = os.getenv('WEBHOOK_BASIC_PASSWORD', '')
    
    def __post_init__(self):
        if self.webhook_headers is None:
            self.webhook_headers = {
                'Content-Type': 'application/json'
            }
        
        token = (self.token or "").strip()
        if token:
            self.webhook_headers['Authorization'] = f"Bearer {token}"

@dataclass
class BrowserConfig:
    """Browser automation configuration."""
    headless: bool = os.getenv('BROWSER_HEADLESS', 'true').lower() == 'true'
    download_timeout: int = int(os.getenv('DOWNLOAD_TIMEOUT', '60'))
    implicit_wait: int = int(os.getenv('IMPLICIT_WAIT', '10'))

@dataclass
class ScheduleConfig:
    """Настройки ежедневного расписания запуска."""
    timezone: str = os.getenv('SCHEDULE_TIMEZONE', 'Europe/Moscow')
    hour: int = int(os.getenv('SCHEDULE_HOUR', '11'))
    minute: int = int(os.getenv('SCHEDULE_MINUTE', '0'))
    run_on_start: bool = os.getenv('RUN_ON_START', 'true').lower() == 'true'

@dataclass
class AppConfig:
    """Main application configuration."""
    email: EmailConfig
    processing: ProcessingConfig
    webhook: WebhookConfig
    browser: BrowserConfig
    schedule: ScheduleConfig
    log_level: str = os.getenv('LOG_LEVEL', 'INFO')
    
    def __init__(self):
        self.email = EmailConfig()
        self.processing = ProcessingConfig()
        self.webhook = WebhookConfig()
        self.browser = BrowserConfig()
        self.schedule = ScheduleConfig()

# Global configuration instance
config = AppConfig()
