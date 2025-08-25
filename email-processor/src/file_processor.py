"""
File processing module for extracting archives and processing CSV files.
"""
import os
import zipfile
import rarfile
import py7zr
import shutil
import pandas as pd
from typing import List, Optional, Dict, Any
from pathlib import Path
from loguru import logger
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.config import config


class FileProcessor:
    """Handles file operations including archive extraction and CSV processing."""
    
    def __init__(self, working_folder: Optional[str] = None):
        self.working_folder = working_folder or config.processing.download_folder
        self.extracted_folder = os.path.join(self.working_folder, "extracted")
        self.processing_config = config.processing
        
        # Ensure folders exist
        os.makedirs(self.working_folder, exist_ok=True)
        os.makedirs(self.extracted_folder, exist_ok=True)
    
    def extract_archive(self, archive_path: str) -> Optional[str]:
        """
        Extract archive file and return path to extracted folder.
        
        Args:
            archive_path (str): Path to archive file
            
        Returns:
            Optional[str]: Path to extracted folder or None if failed
        """
        try:
            if not os.path.exists(archive_path):
                logger.error(f"Archive file not found: {archive_path}")
                return None
            
            # Get file extension
            file_ext = Path(archive_path).suffix.lower()
            archive_name = Path(archive_path).stem
            
            # Create extraction folder
            extract_path = os.path.join(self.extracted_folder, archive_name)
            os.makedirs(extract_path, exist_ok=True)
            
            logger.info(f"Extracting {archive_path} to {extract_path}")
            
            if file_ext == '.zip':
                return self._extract_zip(archive_path, extract_path)
            elif file_ext == '.rar':
                return self._extract_rar(archive_path, extract_path)
            elif file_ext == '.7z':
                return self._extract_7z(archive_path, extract_path)
            else:
                logger.error(f"Unsupported archive format: {file_ext}")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting archive {archive_path}: {e}")
            return None
    
    def _extract_zip(self, archive_path: str, extract_path: str) -> Optional[str]:
        """Extract ZIP archive."""
        try:
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
            logger.info(f"Successfully extracted ZIP: {archive_path}")
            return extract_path
        except Exception as e:
            logger.error(f"Error extracting ZIP {archive_path}: {e}")
            return None
    
    def _extract_rar(self, archive_path: str, extract_path: str) -> Optional[str]:
        """Extract RAR archive."""
        try:
            with rarfile.RarFile(archive_path) as rar_ref:
                rar_ref.extractall(extract_path)
            logger.info(f"Successfully extracted RAR: {archive_path}")
            return extract_path
        except Exception as e:
            logger.error(f"Error extracting RAR {archive_path}: {e}")
            return None
    
    def _extract_7z(self, archive_path: str, extract_path: str) -> Optional[str]:
        """Extract 7Z archive."""
        try:
            with py7zr.SevenZipFile(archive_path, mode='r') as archive:
                archive.extractall(path=extract_path)
            logger.info(f"Successfully extracted 7Z: {archive_path}")
            return extract_path
        except Exception as e:
            logger.error(f"Error extracting 7Z {archive_path}: {e}")
            return None
    
    def find_csv_files(self, folder_path: str) -> List[str]:
        """
        Find all CSV files in folder and subfolders.
        
        Args:
            folder_path (str): Path to search for CSV files
            
        Returns:
            List[str]: List of CSV file paths
        """
        csv_files = []
        
        try:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith('.csv'):
                        csv_path = os.path.join(root, file)
                        csv_files.append(csv_path)
            
            logger.info(f"Found {len(csv_files)} CSV files in {folder_path}")
            return csv_files
            
        except Exception as e:
            logger.error(f"Error finding CSV files in {folder_path}: {e}")
            return csv_files
    
    def process_csv_file(self, csv_path: str) -> List[Dict[str, Any]]:
        """
        Process CSV file and extract payment information based on conditions.
        
        Args:
            csv_path (str): Path to CSV file
            
        Returns:
            List[Dict[str, Any]]: List of payment records
        """
        payments = []
        
        try:
            logger.info(f"Processing CSV file: {csv_path}")
            
            # Read CSV file
            df = pd.read_csv(csv_path)
            logger.info(f"Loaded CSV with {len(df)} rows")
            
            # Apply filter condition
            filter_column = self.processing_config.csv_filter_column
            filter_value = self.processing_config.csv_filter_value
            
            if filter_column in df.columns:
                # Filter rows based on condition
                filtered_df = df[df[filter_column] == filter_value]
                logger.info(f"Filtered to {len(filtered_df)} rows where {filter_column} = {filter_value}")
            else:
                logger.warning(f"Filter column '{filter_column}' not found in CSV. Processing all rows.")
                filtered_df = df
            
            # Extract payment information
            payment_columns = {
                'amount': self.processing_config.payment_amount_column,
                'date': self.processing_config.payment_date_column,
                'transaction_id': self.processing_config.payment_id_column,
                'customer_id': self.processing_config.customer_id_column
            }
            
            for _, row in filtered_df.iterrows():
                payment = {}
                
                # Extract each payment field
                for field_name, column_name in payment_columns.items():
                    if column_name in df.columns:
                        payment[field_name] = self._clean_value(row[column_name])
                    else:
                        logger.warning(f"Column '{column_name}' not found for field '{field_name}'")
                        payment[field_name] = None
                
                # Add any additional fields from the row
                payment['raw_data'] = row.to_dict()
                payment['source_file'] = csv_path
                
                # Only add payment if it has required fields
                if self._is_valid_payment(payment):
                    payments.append(payment)
                else:
                    logger.debug(f"Skipping invalid payment record: {payment}")
            
            logger.info(f"Extracted {len(payments)} valid payment records from {csv_path}")
            return payments
            
        except Exception as e:
            logger.error(f"Error processing CSV file {csv_path}: {e}")
            return payments
    
    def _clean_value(self, value: Any) -> Any:
        """
        Clean and convert value to appropriate type.
        
        Args:
            value: Raw value from CSV
            
        Returns:
            Cleaned value
        """
        if pd.isna(value):
            return None
        
        if isinstance(value, str):
            value = value.strip()
            if value == '' or value.lower() in ['null', 'none', 'n/a']:
                return None
        
        return value
    
    def _is_valid_payment(self, payment: Dict[str, Any]) -> bool:
        """
        Check if payment record has required fields.
        
        Args:
            payment (Dict[str, Any]): Payment record
            
        Returns:
            bool: True if valid payment
        """
        required_fields = ['amount', 'transaction_id']
        
        for field in required_fields:
            if payment.get(field) is None or payment.get(field) == '':
                return False
        
        # Check if amount is numeric
        try:
            amount = payment.get('amount')
            if amount is not None:
                float(str(amount).replace(',', '').replace('$', '').replace('€', '').replace('₽', ''))
        except (ValueError, TypeError):
            logger.warning(f"Invalid amount format: {payment.get('amount')}")
            return False
        
        return True
    
    def process_all_csv_files(self, folder_path: str) -> List[Dict[str, Any]]:
        """
        Process all CSV files in folder and return combined payment data.
        
        Args:
            folder_path (str): Path to folder containing CSV files
            
        Returns:
            List[Dict[str, Any]]: Combined list of payment records
        """
        all_payments = []
        
        try:
            csv_files = self.find_csv_files(folder_path)
            
            if not csv_files:
                logger.warning(f"No CSV files found in {folder_path}")
                return all_payments
            
            for csv_file in csv_files:
                try:
                    payments = self.process_csv_file(csv_file)
                    all_payments.extend(payments)
                except Exception as e:
                    logger.error(f"Error processing {csv_file}: {e}")
                    continue
            
            logger.info(f"Total payments extracted: {len(all_payments)}")
            return all_payments
            
        except Exception as e:
            logger.error(f"Error processing CSV files in {folder_path}: {e}")
            return all_payments
    
    def cleanup_extracted_files(self, keep_recent: int = 5):
        """
        Clean up old extracted files to save disk space.
        
        Args:
            keep_recent (int): Number of recent extractions to keep
        """
        try:
            if not os.path.exists(self.extracted_folder):
                return
            
            # Get all extraction folders sorted by modification time
            folders = []
            for item in os.listdir(self.extracted_folder):
                folder_path = os.path.join(self.extracted_folder, item)
                if os.path.isdir(folder_path):
                    mtime = os.path.getmtime(folder_path)
                    folders.append((folder_path, mtime))
            
            # Sort by modification time (newest first)
            folders.sort(key=lambda x: x[1], reverse=True)
            
            # Remove old folders
            for folder_path, _ in folders[keep_recent:]:
                try:
                    shutil.rmtree(folder_path)
                    logger.info(f"Cleaned up old extraction: {folder_path}")
                except Exception as e:
                    logger.warning(f"Error cleaning up {folder_path}: {e}")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        Get information about a file.
        
        Args:
            file_path (str): Path to file
            
        Returns:
            Dict[str, Any]: File information
        """
        try:
            if not os.path.exists(file_path):
                return {}
            
            stat = os.stat(file_path)
            
            return {
                'path': file_path,
                'name': os.path.basename(file_path),
                'size': stat.st_size,
                'modified_time': stat.st_mtime,
                'extension': Path(file_path).suffix.lower()
            }
            
        except Exception as e:
            logger.error(f"Error getting file info for {file_path}: {e}")
            return {}
