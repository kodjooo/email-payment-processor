"""
File processing module for extracting archives and processing CSV files.
"""
import os
import zipfile
import rarfile
import py7zr
import shutil
import pandas as pd
import re
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
        Process CSV file and extract payment information. 
        Processes all rows EXCEPT those containing CSV_FILTER_VALUE in CSV_FILTER_COLUMN.
        Header row is automatically excluded by pandas.
        
        Payment ID extraction: searches for 4 consecutive digits > 2501 excluding 8000
        from PAYMENT_ID_COLUMN. If not found, uses "-".
        
        Args:
            csv_path (str): Path to CSV file
            
        Returns:
            List[Dict[str, Any]]: List of payment records
        """
        payments = []
        
        try:
            logger.info(f"Processing CSV file: {csv_path}")
            
            # Попробуем определить разделитель автоматически
            # Сначала попробуем с точкой с запятой (типично для русских CSV)
            try:
                df = pd.read_csv(csv_path, sep=';')
                logger.info(f"Loaded CSV with ';' separator. Columns: {list(df.columns)}")
            except Exception:
                # Если не получилось, попробуем с запятой
                df = pd.read_csv(csv_path, sep=',')
                logger.info(f"Loaded CSV with ',' separator. Columns: {list(df.columns)}")
            
            logger.info(f"Loaded CSV with {len(df)} rows")
            logger.info(f"Available columns: {list(df.columns)}")
            
            # Apply filter condition - exclude rows with filter value
            filter_column = self.processing_config.csv_filter_column
            filter_value = self.processing_config.csv_filter_value
            
            if filter_column in df.columns:
                # Filter rows based on condition - exclude rows with filter value
                filtered_df = df[df[filter_column] != filter_value]
                logger.info(f"Filtered to {len(filtered_df)} rows where {filter_column} != {filter_value} (excluding header)")
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
            
            logger.info(f"Looking for columns: {payment_columns}")
            
            for _, row in filtered_df.iterrows():
                payment = {}
                
                # Extract each payment field
                for field_name, column_name in payment_columns.items():
                    if column_name in df.columns:
                        # Use special extraction for transaction_id
                        if field_name == 'transaction_id':
                            payment[field_name] = self._extract_payment_id(row[column_name])
                        else:
                            payment[field_name] = self._clean_value(row[column_name])
                    else:
                        logger.warning(f"Column '{column_name}' not found for field '{field_name}'")
                        # Set default dash for missing transaction_id
                        if field_name == 'transaction_id':
                            payment[field_name] = "-"
                        else:
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
    
    def _extract_payment_id(self, value: Any) -> str:
        """
        Extract payment ID from cell value.
        Improved algorithm:
        1. Looks for contract numbers like C_516913
        2. Looks for 4+ consecutive digits > 2501 excluding 8000  
        3. Returns first 8 characters if nothing found
        
        Args:
            value: Raw value from CSV cell
            
        Returns:
            str: Payment ID or fallback value
        """
        try:
            if pd.isna(value) or value is None:
                return "-"
            
            # Convert to string for processing
            text = str(value).strip()
            
            if not text:
                return "-"
            
            # 1. Look for contract numbers like C_516913, C-516913, etc.
            contract_match = re.search(r'[Cc][-_]?\d{6,}', text)
            if contract_match:
                return contract_match.group(0)
            
            # 2. Look for reference numbers like REF123456 or similar patterns
            ref_match = re.search(r'[A-Za-z]{2,5}[-_]?\d{4,}', text)
            if ref_match:
                return ref_match.group(0)
            
            # 3. Find all 4+ digit numbers in the text (improved pattern)
            # Ищем числа в различных контекстах: "Счёт 2491", "№2497", "счету №2497" и т.д.
            numbers = re.findall(r'(?:счёт|счет|№|#|ID|id)\s*[№#]?\s*(\d{4,})', text, re.IGNORECASE)
            
            for num_str in numbers:
                num = int(num_str)
                # Check conditions: >= 2400 (to include 2491, 2497) and != 8000  
                if num >= 2400 and num != 8000:
                    logger.debug(f"Found payment ID via pattern match: {num_str} from '{text}'")
                    return num_str
            
            # 4. Fallback: Find any 4+ digit numbers in the text
            numbers = re.findall(r'\b\d{4,}\b', text)
            
            for num_str in numbers:
                num = int(num_str)
                # Check conditions: >= 2400 (to include 2491, 2497) and != 8000
                if num >= 2400 and num != 8000:
                    logger.debug(f"Found payment ID via general number match: {num_str} from '{text}'")
                    return num_str
            
            # 5. Fallback: use first 8 characters of cleaned text as ID
            cleaned_text = re.sub(r'[^\w\s-]', '', text)[:8]
            if cleaned_text and cleaned_text != text:
                return cleaned_text
            
            # 6. Last resort: return dash
            return "-"
            
        except Exception as e:
            logger.warning(f"Error extracting payment ID from value '{value}': {e}")
            return "-"
    
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
        # Check amount is present and not empty
        amount = payment.get('amount')
        if amount is None or amount == '':
            return False
        
        # Check transaction_id is present (can be "-" if not found)
        transaction_id = payment.get('transaction_id')
        if transaction_id is None or transaction_id == '':
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
                logger.info(f"Extracted folder {self.extracted_folder} does not exist, nothing to clean")
                return
            
            # Get all extraction folders sorted by modification time
            folders = []
            for item in os.listdir(self.extracted_folder):
                folder_path = os.path.join(self.extracted_folder, item)
                if os.path.isdir(folder_path):
                    mtime = os.path.getmtime(folder_path)
                    folders.append((folder_path, mtime))
            
            logger.info(f"Found {len(folders)} extracted folders, keeping {keep_recent} most recent")
            
            # Sort by modification time (newest first)
            folders.sort(key=lambda x: x[1], reverse=True)
            
            # Keep track of cleanup statistics
            cleaned_count = 0
            cleaned_size = 0
            errors = 0
            
            # Remove old folders
            for folder_path, _ in folders[keep_recent:]:
                try:
                    # Calculate folder size before deletion
                    folder_size = self._get_folder_size(folder_path)
                    shutil.rmtree(folder_path)
                    cleaned_count += 1
                    cleaned_size += folder_size
                    logger.info(f"Cleaned up old extraction: {os.path.basename(folder_path)} ({self._format_size(folder_size)})")
                except Exception as e:
                    errors += 1
                    logger.warning(f"Error cleaning up {folder_path}: {e}")
            
            # Log cleanup summary
            if cleaned_count > 0:
                logger.info(f"Cleanup completed: removed {cleaned_count} folders, freed {self._format_size(cleaned_size)}")
            else:
                logger.info("No old extractions to clean up")
                
            if errors > 0:
                logger.warning(f"Cleanup had {errors} errors")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def _get_folder_size(self, folder_path: str) -> int:
        """Get the total size of a folder in bytes."""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(folder_path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                    except (OSError, FileNotFoundError):
                        pass
        except Exception:
            pass
        return total_size
    
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
