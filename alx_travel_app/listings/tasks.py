from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
import logging
from .models import Booking

# Get logger for payments
logger = logging.getLogger('chapa_payment')

@shared_task
def send_booking_confirmation(booking_id):
    """
    Send booking confirmation email
    """
    logger.info("📧 Starting booking confirmation email task", extra={
        'booking_id': booking_id,
        'action': 'email_task_started'
    })
    
    try:
        booking = Booking.objects.get(id=booking_id)
        user = booking.user
        property = booking.property
        
        subject = f'Booking Confirmation - {booking.reference}'
        
        html_message = render_to_string('emails/booking_confirmation.html', {
            'user': user,
            'booking': booking,
            'property': property,
        })
        
        plain_message = f"""
        Dear {user.get_full_name() or 'Customer'},
        
        Your booking has been confirmed!
        
        Booking Reference: {booking.reference}
        Property: {property.title}
        Check-in: {booking.check_in}
        Check-out: {booking.check_out}
        Total Amount: {booking.total_price}
        
        Thank you for choosing us!
        """
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info("✅ Booking confirmation email sent successfully", extra={
            'booking_id': booking_id,
            'booking_reference': booking.reference,
            'recipient': user.email,
            'action': 'email_sent_success'
        })
        
        return f"Confirmation email sent to {user.email}"
    
    except Booking.DoesNotExist:
        logger.error("❌ Booking not found for email task", extra={
            'booking_id': booking_id,
            'action': 'booking_not_found_email'
        })
        return f"Failed to send email: Booking {booking_id} not found"
    
    except Exception as e:
        logger.error("💥 Failed to send booking confirmation email", extra={
            'booking_id': booking_id,
            'error': str(e),
            'action': 'email_send_failed'
        })
        return f"Failed to send email: {str(e)}"
