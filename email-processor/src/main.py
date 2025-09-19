"""
Main script for the email processor application.
Orchestrates the entire workflow from email processing to webhook sending.
"""
import os
import sys
import time
from typing import List, Dict, Any
from loguru import logger

# Add src directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from email_handler import EmailContextManager
from browser_automation import BrowserContextManager
from file_processor import FileProcessor
from webhook_sender import WebhookSender
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.config import config


class EmailProcessor:
    """Main orchestrator class for the email processing workflow."""
    
    def __init__(self):
        self.file_processor = FileProcessor()
        self.webhook_sender = WebhookSender()
        self.setup_logging()
    
    def setup_logging(self):
        """Set up logging configuration."""
        # Полная очистка всех существующих обработчиков loguru
        logger.remove()
            
        log_level = config.log_level
        log_format = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
        
        # Add console logger
        logger.add(
            sys.stdout,
            level=log_level,
            format=log_format,
            colorize=True
        )
        
        # Add file logger
        log_file = os.path.join("logs", "email_processor.log")
        os.makedirs("logs", exist_ok=True)
        
        logger.add(
            log_file,
            level=log_level,
            format=log_format,
            rotation="10 MB",
            retention="30 days"
        )
        
        logger.info("Email processor started")
    
    def process_emails(self) -> Dict[str, Any]:
        """
        Main processing workflow.
        
        Returns:
            Dict[str, Any]: Processing results summary
        """
        results = {
            "success": False,
            "emails_processed": 0,
            "files_downloaded": 0,
            "payments_found": 0,
            "webhook_sent": False,
            "errors": []
        }
        
        try:
            logger.info("Starting email processing workflow")
            
            # Step 1: Connect to email and find emails with download links
            with EmailContextManager() as email_handler:
                logger.info("Connected to email server")
                
                emails_with_downloads = email_handler.get_latest_emails_with_downloads(limit=10)
                
                if not emails_with_downloads:
                    logger.info("No emails with download links found")
                    results["success"] = True
                    return results
                
                logger.info(f"Found {len(emails_with_downloads)} emails with download links")
                results["emails_processed"] = len(emails_with_downloads)
                
                # Process each email
                all_payments = []
                
                for email_id, download_links in emails_with_downloads:
                    try:
                        logger.info(f"Processing email {email_id} with {len(download_links)} download links")
                        
                        # Step 2: Download files from links
                        downloaded_files = self.download_files(download_links)
                        results["files_downloaded"] += len(downloaded_files)
                        
                        if not downloaded_files:
                            logger.warning(f"No files downloaded from email {email_id}")
                            continue
                        
                        # Step 3: Process downloaded files
                        payments = self.process_downloaded_files(downloaded_files)
                        all_payments.extend(payments)
                        
                        # Mark email as read and processed
                        email_handler.mark_as_read(email_id)
                        email_handler.email_tracker.mark_as_processed(email_id)
                        logger.info(f"Marked email {email_id} as read and processed")
                        
                    except Exception as e:
                        error_msg = f"Error processing email {email_id}: {e}"
                        logger.error(error_msg)
                        results["errors"].append(error_msg)
                        continue
                
                results["payments_found"] = len(all_payments)
                
                # Step 4: Send webhook if payments found
                if all_payments:
                    webhook_success = self.send_webhook(all_payments)
                    results["webhook_sent"] = webhook_success
                    
                    if not webhook_success:
                        results["errors"].append("Failed to send webhook")
                else:
                    logger.info("No payments found to send")
                    results["webhook_sent"] = True  # No payments to send counts as success
                
                # Step 5: Cleanup
                self.cleanup()
                
                results["success"] = len(results["errors"]) == 0
                logger.info(f"Processing completed. Results: {results}")
                
                return results
                
        except Exception as e:
            error_msg = f"Critical error in email processing: {e}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
            return results
    
    def download_files(self, download_links: List[str]) -> List[str]:
        """
        Download files from provided links.
        
        Args:
            download_links (List[str]): List of download URLs
            
        Returns:
            List[str]: List of downloaded file paths
        """
        downloaded_files = []
        
        try:
            with BrowserContextManager(config.processing.download_folder) as browser:
                logger.info(f"Starting download of {len(download_links)} files")
                
                for link in download_links:
                    try:
                        downloaded_file = browser.download_from_url(link)
                        if downloaded_file:
                            downloaded_files.append(downloaded_file)
                            logger.info(f"Downloaded: {downloaded_file}")
                        else:
                            logger.warning(f"Failed to download from: {link}")
                    except Exception as e:
                        logger.error(f"Error downloading from {link}: {e}")
                        continue
                
                logger.info(f"Downloaded {len(downloaded_files)} files successfully")
                return downloaded_files
                
        except Exception as e:
            logger.error(f"Error in download process: {e}")
            return downloaded_files
    
    def process_downloaded_files(self, downloaded_files: List[str]) -> List[Dict[str, Any]]:
        """
        Process downloaded files to extract payment information.
        
        Args:
            downloaded_files (List[str]): List of downloaded file paths
            
        Returns:
            List[Dict[str, Any]]: List of payment records
        """
        all_payments = []
        
        try:
            for file_path in downloaded_files:
                try:
                    logger.info(f"Processing file: {file_path}")
                    
                    # Check if file is an archive
                    file_ext = os.path.splitext(file_path)[1].lower()
                    
                    if file_ext in ['.zip', '.rar', '.7z']:
                        # Extract archive
                        extracted_folder = self.file_processor.extract_archive(file_path)
                        
                        if extracted_folder:
                            # Process CSV files in extracted folder
                            payments = self.file_processor.process_all_csv_files(extracted_folder)
                            all_payments.extend(payments)
                            logger.info(f"Extracted {len(payments)} payments from {file_path}")
                        else:
                            logger.error(f"Failed to extract archive: {file_path}")
                    
                    elif file_ext == '.csv':
                        # Process CSV file directly
                        payments = self.file_processor.process_csv_file(file_path)
                        all_payments.extend(payments)
                        logger.info(f"Extracted {len(payments)} payments from {file_path}")
                    
                    else:
                        logger.warning(f"Unsupported file type: {file_ext} for file {file_path}")
                
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {e}")
                    continue
            
            logger.info(f"Total payments extracted: {len(all_payments)}")
            return all_payments
            
        except Exception as e:
            logger.error(f"Error in file processing: {e}")
            return all_payments
    
    def send_webhook(self, payments: List[Dict[str, Any]]) -> bool:
        """
        Send payment data via webhook.
        
        Args:
            payments (List[Dict[str, Any]]): List of payment records
            
        Returns:
            bool: True if webhook sent successfully
        """
        try:
            logger.info(f"Sending webhook with {len(payments)} payments")
            
            # Send payments in batches
            batch_results = self.webhook_sender.send_webhook_batch(payments, batch_size=50)
            
            success = batch_results.get("success", False)
            
            if success:
                logger.info("Webhook sent successfully")
            else:
                logger.error(f"Webhook sending failed: {batch_results}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending webhook: {e}")
            return False
    
    def cleanup(self):
        """Perform cleanup operations."""
        try:
            logger.info("Performing cleanup")
            
            # Clean up old extracted files
            self.file_processor.cleanup_extracted_files(keep_recent=3)
            
            # Clean up old downloaded archives
            self._cleanup_downloaded_files()
            
            logger.info("Cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def _cleanup_downloaded_files(self, keep_recent: int = 5):
        """Clean up old downloaded archive files."""
        try:
            download_folder = config.processing.download_folder
            if not os.path.exists(download_folder):
                logger.info(f"Download folder {download_folder} does not exist, nothing to clean")
                return
            
            # Get all archive files sorted by modification time
            archives = []
            archive_extensions = ['.zip', '.rar', '.7z', '.tar', '.gz']
            
            for item in os.listdir(download_folder):
                if item.lower().endswith(tuple(archive_extensions)):
                    file_path = os.path.join(download_folder, item)
                    if os.path.isfile(file_path):
                        mtime = os.path.getmtime(file_path)
                        size = os.path.getsize(file_path)
                        archives.append((file_path, mtime, size))
            
            logger.info(f"Found {len(archives)} downloaded archives, keeping {keep_recent} most recent")
            
            # Sort by modification time (newest first)
            archives.sort(key=lambda x: x[1], reverse=True)
            
            # Keep track of cleanup statistics
            cleaned_count = 0
            cleaned_size = 0
            errors = 0
            
            # Remove old archives
            for file_path, _, size in archives[keep_recent:]:
                try:
                    os.remove(file_path)
                    cleaned_count += 1
                    cleaned_size += size
                    logger.info(f"Cleaned up old download: {os.path.basename(file_path)} ({self._format_size(size)})")
                except Exception as e:
                    errors += 1
                    logger.warning(f"Error cleaning up {file_path}: {e}")
            
            # Log cleanup summary
            if cleaned_count > 0:
                logger.info(f"Download cleanup completed: removed {cleaned_count} files, freed {self._format_size(cleaned_size)}")
            else:
                logger.info("No old downloads to clean up")
                
            if errors > 0:
                logger.warning(f"Download cleanup had {errors} errors")
                
        except Exception as e:
            logger.error(f"Error during download cleanup: {e}")
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format."""
        if size_bytes == 0:
            return "0 B"
        size_names = ["B", "KB", "MB", "GB"]
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"
    
    def run_once(self) -> Dict[str, Any]:
        """
        Run the email processor once.
        
        Returns:
            Dict[str, Any]: Processing results
        """
        return self.process_emails()
    
    def run_continuous(self, interval_minutes: int = 30):
        """
        Run the email processor continuously with specified interval.
        
        Args:
            interval_minutes (int): Interval between runs in minutes
        """
        logger.info(f"Starting continuous processing with {interval_minutes} minute intervals")
        
        while True:
            try:
                logger.info("Starting processing cycle")
                results = self.process_emails()
                
                # Log summary
                if results["success"]:
                    logger.info(
                        f"Cycle completed successfully: "
                        f"{results['emails_processed']} emails, "
                        f"{results['files_downloaded']} files, "
                        f"{results['payments_found']} payments"
                    )
                else:
                    logger.error(f"Cycle completed with errors: {results['errors']}")
                
                # Завершаем работу после первого цикла вместо ожидания
                logger.info("Processing cycle completed. Exiting.")
                break
                
            except KeyboardInterrupt:
                logger.info("Received interrupt signal, stopping continuous processing")
                break
            except Exception as e:
                logger.error(f"Unexpected error in continuous processing: {e}")
                time.sleep(60)  # Wait 1 minute before retrying


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Email Payment Processor")
    parser.add_argument(
        "--mode",
        choices=["once", "continuous"],
        default="once",
        help="Run mode: 'once' for single execution, 'continuous' for continuous monitoring"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Interval in minutes for continuous mode (default: 30)"
    )
    
    args = parser.parse_args()
    
    try:
        processor = EmailProcessor()
        
        if args.mode == "once":
            results = processor.run_once()
            print(f"Processing results: {results}")
            
            # Exit with error code if processing failed
            if not results["success"]:
                sys.exit(1)
        
        elif args.mode == "continuous":
            processor.run_continuous(args.interval)
    
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
