import requests
import json
import logging
from django.conf import settings
from django.urls import reverse

logger = logging.getLogger('chapa_payment')

class ChapaService:
    def __init__(self):
        self.secret_key = settings.CHAPA_SECRET_KEY
        self.base_url = settings.CHAPA_BASE_URL
        self.headers = {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json'
        }
        
        # Log initialization (but hide full secret key)
        masked_key = self.secret_key[:8] + '...' + self.secret_key[-4:] if self.secret_key else 'None'
        logger.info(f"ChapaService initialized", extra={
            'base_url': self.base_url,
            'secret_key_masked': masked_key,
            'action': 'chapa_service_init'
        })
    
    def initiate_payment(self, amount, email, first_name, last_name, tx_ref, 
                       return_url, currency='ETB', custom_title=None, custom_description=None):
        """
        Initiate payment with Chapa API - Enhanced debugging
        """
        url = f"{self.base_url}/transaction/initialize"
        
        payload = {
            "amount": str(amount),
            "currency": currency,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "tx_ref": tx_ref,
            "return_url": return_url,
            "customization": {
                "title": custom_title or "Property Booking Payment",
                "description": custom_description or "Secure payment for your property booking"
            }
        }
        
        # Enhanced logging
        logger.info("🔗 Initiating Chapa payment with details:", extra={
            'transaction_id': tx_ref,
            'amount': amount,
            'currency': currency,
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'return_url': return_url,
            'chapa_url': url,
            'action': 'payment_initiation_start'
        })
        
        logger.debug("Chapa API Request Payload:", extra={
            'payload': payload,
            'headers': {k: '***' if 'Authorization' in k else v for k, v in self.headers.items()},
            'action': 'chapa_request_details'
        })
        
        try:
            response = requests.post(url, json=payload, headers=self.headers, timeout=30)
            
            # Log the raw response for debugging
            logger.debug("Chapa API Raw Response:", extra={
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'response_text': response.text,
                'action': 'chapa_raw_response'
            })
            
            response.raise_for_status()
            
            data = response.json()
            
            # Log successful initiation
            logger.info("✅ Chapa payment initiated successfully", extra={
                'transaction_id': tx_ref,
                'checkout_url': data.get('data', {}).get('checkout_url'),
                'status': data.get('data', {}).get('status'),
                'chapa_message': data.get('message'),
                'action': 'payment_initiation_success'
            })
            
            return {
                'success': True,
                'checkout_url': data['data']['checkout_url'],
                'transaction_id': data['data']['tx_ref'],
                'response_data': data
            }
            
        except requests.exceptions.RequestException as e:
            # Enhanced error logging
            error_details = {
                'transaction_id': tx_ref,
                'error_type': type(e).__name__,
                'error_message': str(e),
                'action': 'payment_initiation_failed'
            }
            
            # Add response details if available
            if hasattr(e, 'response') and e.response is not None:
                error_details.update({
                    'response_status': e.response.status_code,
                    'response_headers': dict(e.response.headers),
                    'response_body': e.response.text
                })
            
            logger.error("❌ Chapa payment initiation failed with details:", extra=error_details)
            
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to initiate payment with Chapa'
            }
        except Exception as e:
            logger.error("❌ Unexpected error in Chapa payment initiation:", extra={
                'transaction_id': tx_ref,
                'error': str(e),
                'error_type': type(e).__name__,
                'action': 'payment_initiation_unexpected_error'
            })
            
            return {
                'success': False,
                'error': str(e),
                'message': 'Unexpected error during payment initiation'
            }