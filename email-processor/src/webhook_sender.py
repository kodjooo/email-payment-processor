"""
Webhook sender module for transmitting payment data to external servers.
"""
import json
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.config import config


class WebhookSender:
    """Handles sending payment data via webhooks to external servers."""
    
    def __init__(self):
        self.webhook_config = config.webhook
        self.session = requests.Session()
        
        # Set default headers
        self.session.headers.update(self.webhook_config.webhook_headers)
        
        username = (self.webhook_config.basic_username or "").strip()
        password = (self.webhook_config.basic_password or "").strip()
        if username and password:
            self.session.auth = (username, password)
    
    def format_payment_data(self, payments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Format payment data for webhook transmission.
        
        Args:
            payments (List[Dict[str, Any]]): List of payment records
            
        Returns:
            Dict[str, Any]: Formatted webhook payload
        """
        try:
            # Prepare webhook payload
            webhook_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "payments_count": len(payments),
                    "payments": []
                }
            }
            
            # Format each payment
            for payment in payments:
                # Получаем назначение платежа из raw_data
                purpose = None
                raw_data = payment.get("raw_data", {})
                if raw_data:
                    purpose = raw_data.get("Назначение платежа") or raw_data.get("назначение платежа")
                
                formatted_payment = {
                    "transaction_id": payment.get("transaction_id"),
                    "customer_id": payment.get("customer_id"),
                    "amount": self._format_amount(payment.get("amount")),
                    "currency": self._extract_currency(payment.get("amount")),
                    "date": self._format_date(payment.get("date")),
                    "purpose": purpose,  # Полное назначение платежа
                    "source_file": payment.get("source_file", "").split("/")[-1] if payment.get("source_file") else None
                }
                
                # Add any additional fields that might be useful
                raw_data = payment.get("raw_data", {})
                if raw_data:
                    # Include select additional fields
                    additional_fields = [
                        "description", "reference", "account", "bank", 
                        "method", "fee", "tax", "net_amount"
                    ]
                    
                    for field in additional_fields:
                        if field in raw_data and raw_data[field] is not None:
                            formatted_payment["metadata"][field] = raw_data[field]
                
                webhook_data["data"]["payments"].append(formatted_payment)
            
            return webhook_data
            
        except Exception as e:
            logger.error(f"Error formatting payment data: {e}")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": "payments_processed",
                "error": str(e),
                "data": {"payments_count": 0, "payments": []}
            }
    
    def _format_amount(self, amount: Any) -> Optional[float]:
        """
        Format amount to float value.
        
        Args:
            amount: Raw amount value
            
        Returns:
            Optional[float]: Formatted amount or None
        """
        if amount is None:
            return None
        
        try:
            # Remove common currency symbols and formatting
            amount_str = str(amount).replace(',', '.').replace('$', '').replace('€', '').replace('₽', '').strip()
            amount_float = float(amount_str)
            # Return int if it's a whole number, otherwise return float
            return int(amount_float) if amount_float.is_integer() else amount_float
        except (ValueError, TypeError):
            logger.warning(f"Could not format amount: {amount}")
            return None
    
    def _extract_currency(self, amount: Any) -> str:
        """
        Extract currency from amount string.
        
        Args:
            amount: Raw amount value
            
        Returns:
            str: Currency code or 'USD' as default
        """
        if amount is None:
            return "USD"
        
        amount_str = str(amount)
        
        # Common currency mappings
        currency_map = {
            '$': 'USD',
            '€': 'EUR',
            '₽': 'RUB',
            '£': 'GBP',
            '¥': 'JPY'
        }
        
        for symbol, code in currency_map.items():
            if symbol in amount_str:
                return code
        
        return "RUB"  # Default currency
    
    def _format_date(self, date_value: Any) -> Optional[str]:
        """
        Format date to ISO format.
        
        Args:
            date_value: Raw date value
            
        Returns:
            Optional[str]: ISO formatted date or None
        """
        if date_value is None:
            return None
        
        try:
            # Try to parse common date formats
            from dateutil import parser
            parsed_date = parser.parse(str(date_value))
            return parsed_date.isoformat()
        except Exception:
            logger.warning(f"Could not parse date: {date_value}")
            return str(date_value) if date_value else None
    
    def _generate_summary(self, payments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate summary statistics for payments.
        
        Args:
            payments (List[Dict[str, Any]]): List of payment records
            
        Returns:
            Dict[str, Any]: Payment summary
        """
        try:
            if not payments:
                return {
                    "total_amount": 0,
                    "currency": "RUB",
                    "count": 0,
                    "unique_customers": 0
                }
            
            total_amount = 0
            currencies = set()
            customer_ids = set()
            
            for payment in payments:
                # Sum amounts
                amount = self._format_amount(payment.get("amount"))
                if amount:
                    total_amount += amount
                
                # Collect currencies
                currency = self._extract_currency(payment.get("amount"))
                currencies.add(currency)
                
                # Collect customer IDs
                customer_id = payment.get("customer_id")
                if customer_id:
                    customer_ids.add(customer_id)
            
            return {
                "total_amount": int(total_amount) if total_amount == int(total_amount) else round(total_amount, 2),
                "currencies": list(currencies),
                "primary_currency": list(currencies)[0] if currencies else "RUB",
                "count": len(payments),
                "unique_customers": len(customer_ids),
                "date_range": self._get_date_range(payments)
            }
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return {
                "total_amount": 0,
                "currency": "RUB",
                "count": len(payments),
                "unique_customers": 0,
                "error": str(e)
            }
    
    def _get_date_range(self, payments: List[Dict[str, Any]]) -> Dict[str, Optional[str]]:
        """
        Get date range from payments.
        
        Args:
            payments (List[Dict[str, Any]]): List of payment records
            
        Returns:
            Dict[str, Optional[str]]: Date range with earliest and latest dates
        """
        dates = []
        
        for payment in payments:
            date_value = payment.get("date")
            if date_value:
                formatted_date = self._format_date(date_value)
                if formatted_date:
                    dates.append(formatted_date)
        
        if not dates:
            return {"earliest": None, "latest": None}
        
        dates.sort()
        return {
            "earliest": dates[0],
            "latest": dates[-1]
        }
    
    def send_webhook(self, payments: List[Dict[str, Any]]) -> bool:
        """
        Send payment data via webhook.
        
        Args:
            payments (List[Dict[str, Any]]): List of payment records
            
        Returns:
            bool: True if webhook sent successfully, False otherwise
        """
        try:
            if not self.webhook_config.webhook_url:
                logger.error("Webhook URL not configured")
                return False
            
            if not payments:
                logger.warning("No payments to send")
                return True
            
            # Format payment data
            webhook_payload = self.format_payment_data(payments)
            
            # Полный вывод данных вебхука в лог
            logger.info(f"Sending webhook with {len(payments)} payments to {self.webhook_config.webhook_url}")
            logger.info(f"Webhook payload:")
            logger.info(f"  - Timestamp: {webhook_payload.get('timestamp')}")
            logger.info(f"  - Total payments: {webhook_payload.get('data', {}).get('payments_count', 0)}")
            
            # Источники файлов (один раз для всего вебхука)
            source_files = set()
            payments_data = webhook_payload.get('data', {}).get('payments', [])
            for payment in payments_data:
                if payment.get('source_file'):
                    source_files.add(payment.get('source_file'))
            
            if source_files:
                logger.info(f"  - Source files: {', '.join(source_files)}")
            
            # Детальная информация о каждом платеже
            for i, payment in enumerate(payments_data, 1):
                logger.info(f"  Payment {i}:")
                logger.info(f"    - Transaction ID: {payment.get('transaction_id')}")
                logger.info(f"    - Customer ID: {payment.get('customer_id')}")
                logger.info(f"    - Amount: {payment.get('amount')}")
                logger.info(f"    - Currency: {payment.get('currency')}")
                # Показываем только дату без времени
                date_str = payment.get('date', '')
                if 'T' in date_str:
                    date_only = date_str.split('T')[0]
                    logger.info(f"    - Date: {date_only}")
                else:
                    logger.info(f"    - Date: {date_str}")
                logger.info(f"    - Purpose: {payment.get('purpose')}")
            
            # Полный JSON payload для отладки (в debug режиме)
            logger.debug(f"Full webhook payload JSON: {json.dumps(webhook_payload, ensure_ascii=False, indent=2)}")
            
            # Send POST request
            response = self.session.post(
                self.webhook_config.webhook_url,
                json=webhook_payload,
                timeout=self.webhook_config.webhook_timeout
            )
            
            # Логирование отправленного вебхука
            logger.info(f"Webhook sent to {self.webhook_config.webhook_url}")
            logger.info(f"Request headers: {dict(self.session.headers)}")
            
            # Check response
            if response.status_code in [200, 201, 202]:
                logger.info(f"Webhook sent successfully. Response: {response.status_code}")
                
                # Детальное логирование ответа сервера
                logger.info(f"Response headers: {dict(response.headers)}")
                logger.info(f"Response time: {response.elapsed.total_seconds():.2f}s")
                
                # Log response content if available
                try:
                    response_data = response.json()
                    logger.info(f"Server response (JSON): {json.dumps(response_data, ensure_ascii=False, indent=2)}")
                except:
                    if response.text:
                        logger.info(f"Server response (text): {response.text[:1000]}")
                    else:
                        logger.info("Server response: (empty)")
                
                return True
            else:
                logger.error(f"Webhook failed with status {response.status_code}")
                logger.error(f"Response headers: {dict(response.headers)}")
                logger.error(f"Response time: {response.elapsed.total_seconds():.2f}s")
                
                # Логируем полный ответ при ошибке
                if response.text:
                    logger.error(f"Error response: {response.text[:1000]}")
                else:
                    logger.error("Error response: (empty)")
                
                return False
                
        except requests.exceptions.Timeout:
            logger.error("Webhook request timed out")
            return False
        except requests.exceptions.ConnectionError:
            logger.error("Failed to connect to webhook URL")
            return False
        except Exception as e:
            logger.error(f"Error sending webhook: {e}")
            return False
    
    def send_webhook_batch(
        self, 
        payments: List[Dict[str, Any]], 
        batch_size: int = 50
    ) -> Dict[str, Any]:
        """
        Send payments in batches via webhook.
        
        Args:
            payments (List[Dict[str, Any]]): List of payment records
            batch_size (int): Number of payments per batch
            
        Returns:
            Dict[str, Any]: Results summary
        """
        try:
            if not payments:
                return {
                    "success": True,
                    "total_payments": 0,
                    "batches_sent": 0,
                    "failed_batches": 0
                }
            
            total_payments = len(payments)
            batches_sent = 0
            failed_batches = 0
            
            # Split payments into batches
            for i in range(0, total_payments, batch_size):
                batch = payments[i:i + batch_size]
                
                logger.info(f"Sending batch {batches_sent + 1} with {len(batch)} payments")
                
                if self.send_webhook(batch):
                    batches_sent += 1
                else:
                    failed_batches += 1
                    logger.error(f"Failed to send batch {batches_sent + failed_batches}")
            
            success_rate = batches_sent / (batches_sent + failed_batches) if (batches_sent + failed_batches) > 0 else 0
            
            result = {
                "success": failed_batches == 0,
                "total_payments": total_payments,
                "batches_sent": batches_sent,
                "failed_batches": failed_batches,
                "success_rate": success_rate
            }
            
            logger.info(f"Webhook batch results: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error sending webhook batches: {e}")
            return {
                "success": False,
                "error": str(e),
                "total_payments": len(payments),
                "batches_sent": 0,
                "failed_batches": 0
            }
    
    def test_webhook_connection(self) -> bool:
        """
        Test webhook connection with a simple ping.
        
        Returns:
            bool: True if connection successful
        """
        try:
            if not self.webhook_config.webhook_url:
                logger.error("Webhook URL not configured")
                return False
            
            # Send test payload
            test_payload = {
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": "connection_test",
                "data": {"message": "Test connection from email processor"}
            }
            
            response = self.session.post(
                self.webhook_config.webhook_url,
                json=test_payload,
                timeout=10
            )
            
            success = response.status_code in [200, 201, 202]
            
            if success:
                logger.info("Webhook connection test successful")
            else:
                logger.warning(f"Webhook connection test failed: {response.status_code}")
            
            return success
            
        except Exception as e:
            logger.error(f"Webhook connection test failed: {e}")
            return False
