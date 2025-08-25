"""
Browser automation module for clicking download links and handling file downloads.
"""
import os
import time
import glob
from typing import Optional, List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from loguru import logger
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.config import config


class BrowserAutomation:
    """Handles browser automation for downloading files from web links."""
    
    def __init__(self, download_folder: Optional[str] = None):
        self.download_folder = download_folder or config.processing.download_folder
        self.browser_config = config.browser
        self.driver = None
        
        # Ensure download folder exists
        os.makedirs(self.download_folder, exist_ok=True)
    
    def setup_driver(self) -> bool:
        """
        Set up Chrome WebDriver with appropriate options.
        
        Returns:
            bool: True if setup successful, False otherwise
        """
        try:
            # Chrome options
            chrome_options = Options()
            
            if self.browser_config.headless:
                chrome_options.add_argument("--headless")
            
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            
            # Set download preferences
            prefs = {
                "download.default_directory": os.path.abspath(self.download_folder),
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            # Set up Chrome driver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Set implicit wait
            self.driver.implicitly_wait(self.browser_config.implicit_wait)
            
            logger.info("Browser driver setup completed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup browser driver: {e}")
            return False
    
    def cleanup_driver(self):
        """Clean up browser driver."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser driver closed")
            except Exception as e:
                logger.warning(f"Error closing browser driver: {e}")
    
    def download_from_url(self, url: str, timeout: Optional[int] = None) -> Optional[str]:
        """
        Download file from URL by navigating to it and handling any download buttons.
        
        Args:
            url (str): URL to download from
            timeout (int): Download timeout in seconds
            
        Returns:
            Optional[str]: Path to downloaded file or None if failed
        """
        timeout = timeout or self.browser_config.download_timeout
        
        try:
            if not self.driver:
                if not self.setup_driver():
                    return None
            
            logger.info(f"Navigating to download URL: {url}")
            
            # Get initial file count
            initial_files = self._get_download_files()
            
            # Navigate to URL
            self.driver.get(url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Try to find and click download button/link
            downloaded_file = self._handle_download_page(timeout, initial_files)
            
            if downloaded_file:
                logger.info(f"Successfully downloaded: {downloaded_file}")
                return downloaded_file
            else:
                logger.warning(f"No file was downloaded from {url}")
                return None
                
        except Exception as e:
            logger.error(f"Error downloading from {url}: {e}")
            return None
    
    def _handle_download_page(self, timeout: int, initial_files: List[str]) -> Optional[str]:
        """
        Handle download page by finding and clicking download elements.
        
        Args:
            timeout (int): Timeout for download completion
            initial_files (List[str]): List of files before download
            
        Returns:
            Optional[str]: Path to downloaded file
        """
        try:
            # Common download button selectors and texts
            download_selectors = [
                "//a[contains(@class, 'download')]",
                "//button[contains(@class, 'download')]",
                "//a[contains(text(), 'Download')]",
                "//button[contains(text(), 'Download')]",
                "//a[contains(text(), 'Скачать')]",
                "//button[contains(text(), 'Скачать')]",
                "//input[@type='submit'][contains(@value, 'download')]",
                "//a[contains(@href, 'download')]",
                "//a[contains(@href, '.zip')]",
                "//a[contains(@href, '.rar')]",
                "//a[contains(@href, '.7z')]"
            ]
            
            download_element = None
            
            # Try to find download element
            for selector in download_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements:
                        # Filter for visible elements
                        visible_elements = [el for el in elements if el.is_displayed()]
                        if visible_elements:
                            download_element = visible_elements[0]
                            logger.info(f"Found download element with selector: {selector}")
                            break
                except Exception:
                    continue
            
            if download_element:
                # Click download element
                self.driver.execute_script("arguments[0].click();", download_element)
                logger.info("Clicked download element")
                
                # Wait for download to complete
                return self._wait_for_download(timeout, initial_files)
            else:
                # If no specific download button found, check if file download started automatically
                logger.info("No download button found, checking for automatic download")
                return self._wait_for_download(timeout, initial_files)
                
        except Exception as e:
            logger.error(f"Error handling download page: {e}")
            return None
    
    def _wait_for_download(self, timeout: int, initial_files: List[str]) -> Optional[str]:
        """
        Wait for file download to complete.
        
        Args:
            timeout (int): Timeout in seconds
            initial_files (List[str]): Files before download started
            
        Returns:
            Optional[str]: Path to downloaded file
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                current_files = self._get_download_files()
                
                # Check for new files
                new_files = [f for f in current_files if f not in initial_files]
                
                if new_files:
                    # Check if download is complete (no .crdownload or .tmp files)
                    complete_files = [
                        f for f in new_files 
                        if not f.endswith(('.crdownload', '.tmp', '.part'))
                    ]
                    
                    if complete_files:
                        return complete_files[0]  # Return first complete file
                
                # Check for .crdownload files that might have completed
                crdownload_files = glob.glob(os.path.join(self.download_folder, "*.crdownload"))
                if not crdownload_files:
                    # If there were crdownload files before but not now, check for new complete files
                    current_files_again = self._get_download_files()
                    new_complete_files = [f for f in current_files_again if f not in initial_files]
                    if new_complete_files:
                        return new_complete_files[0]
                
                time.sleep(1)  # Wait before checking again
                
            except Exception as e:
                logger.error(f"Error checking download progress: {e}")
                time.sleep(1)
        
        logger.warning(f"Download timeout after {timeout} seconds")
        return None
    
    def _get_download_files(self) -> List[str]:
        """
        Get list of files in download folder.
        
        Returns:
            List[str]: List of file paths
        """
        try:
            if not os.path.exists(self.download_folder):
                return []
            
            files = []
            for file in os.listdir(self.download_folder):
                file_path = os.path.join(self.download_folder, file)
                if os.path.isfile(file_path):
                    files.append(file_path)
            
            return files
            
        except Exception as e:
            logger.error(f"Error getting download files: {e}")
            return []
    
    def download_multiple_urls(self, urls: List[str]) -> List[str]:
        """
        Download files from multiple URLs.
        
        Args:
            urls (List[str]): List of URLs to download from
            
        Returns:
            List[str]: List of successfully downloaded file paths
        """
        downloaded_files = []
        
        try:
            if not self.setup_driver():
                return downloaded_files
            
            for url in urls:
                try:
                    downloaded_file = self.download_from_url(url)
                    if downloaded_file:
                        downloaded_files.append(downloaded_file)
                    
                    # Small delay between downloads
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error downloading from {url}: {e}")
                    continue
            
            return downloaded_files
            
        finally:
            self.cleanup_driver()


# Context manager for browser automation
class BrowserContextManager:
    """Context manager for BrowserAutomation to ensure proper cleanup."""
    
    def __init__(self, download_folder: Optional[str] = None):
        self.automation = BrowserAutomation(download_folder)
    
    def __enter__(self) -> BrowserAutomation:
        if not self.automation.setup_driver():
            raise Exception("Failed to setup browser driver")
        return self.automation
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.automation.cleanup_driver()
