from django.shortcuts import render, get_object_or_404
from alx_travel_app.listings.tasks import send_booking_confirmation
from rest_framework import viewsets, status
from .models import Listing, Booking, User, Payment
from rest_framework.response import Response
from .serializers import ListingSerializer, BookingSerializer, PaymentSerializer, PaymentInitiationSerializer
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action, api_view, permission_classes
from django.db.models import Avg
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from django.urls import reverse
from .chapa_service import ChapaService
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
import logging
import uuid

logger = logging.getLogger('chapa_payment')

# Create your views here.
class ListingViewSet(viewsets.ModelViewSet):
    # Ensuring CRUD operations for Listing model
    queryset = Listing.objects.all()
    serializer_class = ListingSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['property_type', 'price_per_night']
    search_fields = ['title', 'description', 'address', 'amenities']
    ordering_fields = ['price_per_night', 'created_at']

    def get_queryset(self):
        # filter the queryset to include related host and reviews for optimization
        queryset = Listing.objects.select_related('host').prefetch_related('reviews').all()
        
        # filter by avalability if start_date and end_date are provided in query params
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.exclude(
                bookings__start_date__lt=end_date,
                bookings__end_date__gt=start_date
            )
        
        # filter by price range if min_price and max_price are provided in query params
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        if min_price and max_price:
            queryset = queryset.filter(price_per_night__gte=min_price, price_per_night__lte=max_price)
            queryset = queryset.annotate(average_rating=Avg('reviews__rating'))
            queryset = queryset.order_by('-average_rating')

        return queryset.distinct()

    def perform_create(self, serializer):
        # Automatically set the host to the logged-in user when creating a listing
        serializer.save(host=self.request.user)

    @action(detail=True, methods=['get'])
    def bookings(self, request, pk=None):
        # Retrieve bookings for a specific listing
        listing = self.get_object()
        bookings = listing.bookings.all()
        serializer = BookingSerializer(bookings, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def create_booking(self, request, pk=None):
        # Create a new booking for a specific listing
        listing = self.get_object()
        serializer = BookingSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(listing=listing, user=request.user)
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)
    
    @action(detail=False, methods=['get'])
    def my_listings(self, request):
        # Retrieve listings for the logged-in user
        user = request.user
        listings = Listing.objects.filter(host=user)
        serializer = self.get_serializer(listings, many=True)
        return Response(serializer.data)

class BookingViewSet(viewsets.ModelViewSet):
    # Ensuring CRUD operations for Booking model
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['start_date', 'end_date', 'total_price']
    search_fields = ['listing__title', 'user__username']
    ordering_fields = ['start_date', 'end_date', 'total_price']

    def get_queryset(self):
        # users can only see their own bookings unless they are staff
        user = self.request.user
        queryset = Booking.objects.select_related('listing', 'user').all()
        if not user.is_staff:
            queryset = queryset.filter(user=user)

        # filter by date range if start_date and end_date are provided in query params
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(start_date__gte=start_date, end_date__lte=end_date)

        # filter by listing title if listing_title is provided in query params
        listing_title = self.request.query_params.get('listing_title')
        if listing_title:
            queryset = queryset.filter(listing__title__icontains=listing_title)
        return queryset.distinct()
    
    def perform_create(self, serializer):
        # Save the booking instance
        booking = serializer.save()

        # Prepare email content
        user_email = booking.user.email if booking.user else None
        if user_email:
            booking_id = (
                f"Booking ID: {booking.id}\n"
                f"Destination: {booking.destination}\n"
                f"Date: {booking.date}\n"
                f"Status: {booking.status}\n"
                f"Created at: {booking.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
            )

            # Trigger Celery background task
            send_booking_confirmation.delay(booking_id)

    @action(detail=False, methods=['get'])
    def my_bookings(self, request):
        # Retrieve bookings for the logged-in user
        user = request.user
        bookings = Booking.objects.filter(user=user)
        serializer = self.get_serializer(bookings, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def host_bookings(self, request):
        # Retrieve bookings for listings owned by the logged-in host
        user = request.user
        listings = Listing.objects.filter(host=user)
        bookings = Booking.objects.filter(listing__in=listings)
        serializer = self.get_serializer(bookings, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        # Cancel a specific booking
        booking = self.get_object()
        if booking.user != request.user and not request.user.is_staff:
            return Response({'error': 'You do not have permission to cancel this booking.'}, status=403)
        booking.delete()
        return Response({'status': 'Booking cancelled'}, status=204)
    
    @action(detail=True, methods=['post'])
    def reschedule(self, request, pk=None):
        # Reschedule a specific booking
        booking = self.get_object()
        if booking.user != request.user and not request.user.is_staff:
            return Response({'error': 'You do not have permission to reschedule this booking.'}, status=403)
        serializer = BookingSerializer(booking, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)
    
    @action(detail=True, methods=['get'])
    def confirm(self, request, pk=None):
        # Confirm a specific booking (for hosts)
        booking = self.get_object()
        if booking.listing.host != request.user and not request.user.is_staff:
            return Response({'error': 'You do not have permission to confirm this booking.'}, status=403)
        # Here you can add logic to mark the booking as confirmed
        return Response({'status': 'Booking confirmed'}, status=200)
    
    @action(detail=True, methods=['post'])
    def initiate_payment(self, request, pk=None):
        """
        Initiate payment for this booking
        """
        booking = self.get_object()
        
        # Check if booking belongs to user
        if booking.user != request.user and not request.user.is_staff:
            return Response(
                {'error': 'You do not have permission to pay for this booking.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if payment already exists
        if hasattr(booking, 'payment'):
            return Response(
                {'error': 'Payment already exists for this booking.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response({
            'message': 'Use the /api/payments/ endpoint to create payment for this booking.'
        })


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'  # Use UUID as lookup field
    
    def get_queryset(self):
        """
        Users can only see payments for their own bookings unless they are staff
        """
        user = self.request.user
        queryset = Payment.objects.select_related('booking', 'booking__user', 'booking__listing').all()
        
        if not user.is_staff:
            queryset = queryset.filter(booking__user=user)
        
        return queryset
    
    def create(self, request, *args, **kwargs):
        """
        Create a payment for a booking - Updated for UUID
        """
        serializer = PaymentInitiationSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        booking_id = serializer.validated_data['booking_id']
        
        try:
            # Get the booking using UUID
            booking = get_object_or_404(Booking, id=booking_id)
            
            logger.info("Processing payment for booking", extra={
                'booking_id': str(booking_id),
                'user': request.user.email,
                'action': 'payment_processing_start'
            })
            
            # Generate unique transaction reference with UUID
            transaction_id = f"txn_{uuid.uuid4().hex[:10]}_{booking_id.hex[:8]}"
            
            # Prepare return URL
            return_url = request.build_absolute_uri(
                reverse('payment-success')
            ) + f"?booking={booking_id}"
            
            # Initialize Chapa service
            chapa = ChapaService()
            
            # Get user details
            user = booking.user
            first_name = user.first_name or 'Customer'
            last_name = user.last_name or 'User'
            
            # Log payment details
            logger.info("Payment details", extra={
                'booking_id': str(booking_id),
                'amount': float(booking.total_price),
                'user_email': user.email,
                'transaction_id': transaction_id,
                'action': 'payment_details'
            })
            
            # Initiate payment with Chapa
            payment_result = chapa.initiate_payment(
                amount=float(booking.total_price),
                email=user.email,
                first_name=first_name,
                last_name=last_name,
                tx_ref=transaction_id,
                return_url=return_url,
                custom_title=f"Payment for {booking.listing.title}",
                custom_description=f"Booking reference: {booking_id}"
            )
            
            if not payment_result['success']:
                logger.error("Payment initiation failed", extra={
                    'booking_id': str(booking_id),
                    'error': payment_result.get('message'),
                    'action': 'payment_initiation_failed'
                })
                return Response(
                    {'error': payment_result['message']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create payment record
            payment = Payment.objects.create(
                booking=booking,
                transaction_id=transaction_id,
                amount=booking.total_price,
                status='pending',
                chapa_reference=transaction_id,
                initiation_response=payment_result.get('response_data')
            )
            
            logger.info("Payment record created successfully", extra={
                'payment_id': str(payment.id),
                'booking_id': str(booking_id),
                'transaction_id': transaction_id,
                'action': 'payment_created'
            })
            
            # Serialize the response
            response_serializer = PaymentSerializer(payment)
            
            return Response({
                'success': True,
                'payment': response_serializer.data,
                'checkout_url': payment_result['checkout_url'],
                'message': 'Payment initiated successfully. Redirect to checkout URL to complete payment.'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error("Unexpected error in payment creation", extra={
                'booking_id': str(booking_id),
                'error': str(e),
                'action': 'payment_creation_error'
            })
            return Response(
                {'error': f'An unexpected error occurred: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def retry_payment(self, request, id=None):  # Changed pk to id for UUID
        """
        Retry payment for a failed payment - Updated for UUID
        """
        payment = self.get_object()
        
        logger.info("Retrying payment", extra={
            'payment_id': str(payment.id),
            'booking_id': str(payment.booking.id),
            'action': 'payment_retry_start'
        })
        
        # Generate new transaction ID with UUID
        new_transaction_id = f"txn_{uuid.uuid4().hex[:10]}_{payment.booking.id.hex[:8]}"
        
        # Prepare return URL
        return_url = request.build_absolute_uri(
            reverse('payment-success')
        ) + f"?booking={payment.booking.id}"
        
        # Initialize Chapa service
        chapa = ChapaService()
        
        # Get user details
        user = payment.booking.user
        first_name = user.first_name or 'Customer'
        last_name = user.last_name or 'User'
        
        # Initiate new payment
        payment_result = chapa.initiate_payment(
            amount=float(payment.amount),
            email=user.email,
            first_name=first_name,
            last_name=last_name,
            tx_ref=new_transaction_id,
            return_url=return_url,
            custom_title=f"Payment for {payment.booking.listing.title}",
            custom_description=f"Booking reference: {payment.booking.id}"
        )
        
        if not payment_result['success']:
            logger.error("Payment retry failed", extra={
                'payment_id': str(payment.id),
                'error': payment_result.get('message'),
                'action': 'payment_retry_failed'
            })
            return Response(
                {'error': payment_result['message']},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update payment record
        payment.transaction_id = new_transaction_id
        payment.status = 'pending'
        payment.chapa_reference = new_transaction_id
        payment.initiation_response = payment_result.get('response_data')
        payment.verification_response = None
        payment.paid_at = None
        payment.save()
        
        logger.info("Payment retry successful", extra={
            'payment_id': str(payment.id),
            'new_transaction_id': new_transaction_id,
            'action': 'payment_retry_success'
        })
        
        return Response({
            'success': True,
            'checkout_url': payment_result['checkout_url'],
            'transaction_id': new_transaction_id,
            'message': 'Payment retry initiated successfully. Redirect to checkout URL.'
        })
    
    @action(detail=False, methods=['get'])
    def status(self, request):
        """
        Get payment status by transaction ID or booking ID - Updated for UUID
        """
        transaction_id = request.query_params.get('transaction_id')
        booking_id = request.query_params.get('booking_id')
        
        logger.info("Payment status check", extra={
            'transaction_id': transaction_id,
            'booking_id': booking_id,
            'action': 'payment_status_check'
        })
        
        if not transaction_id and not booking_id:
            return Response(
                {'error': 'Either transaction_id or booking_id is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            if transaction_id:
                payment = Payment.objects.get(transaction_id=transaction_id)
            else:
                # Convert string booking_id to UUID
                from django.core.exceptions import ValidationError
                try:
                    booking_uuid = uuid.UUID(booking_id)
                    booking = Booking.objects.get(id=booking_uuid)
                    payment = Payment.objects.get(booking=booking)
                except (ValueError, ValidationError):
                    return Response(
                        {'error': 'Invalid booking ID format.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Check permissions
            if payment.booking.user != request.user and not request.user.is_staff:
                return Response(
                    {'error': 'You do not have permission to view this payment.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            serializer = self.get_serializer(payment)
            return Response(serializer.data)
            
        except (Payment.DoesNotExist, Booking.DoesNotExist):
            return Response(
                {'error': 'Payment not found.'},
                status=status.HTTP_404_NOT_FOUND
            )


@method_decorator(csrf_exempt, name='dispatch')
class ChapaWebhookView(APIView):
    """
    Handle Chapa webhook for payment notifications
    """
    authentication_classes = []  # No authentication for webhooks
    permission_classes = []
    
    def post(self, request):
        try:
            webhook_data = request.data
            transaction_id = webhook_data.get('tx_ref')
            event_type = webhook_data.get('event')
            
            logger.info("Webhook received", extra={
                'transaction_id': transaction_id,
                'event_type': event_type,
                'action': 'webhook_received'
            })
            
            if not transaction_id:
                logger.error("Webhook missing transaction reference", extra={
                    'action': 'webhook_missing_tx_ref'
                })
                return Response({'error': 'No transaction reference'}, status=400)
            
            # Find payment
            try:
                payment = Payment.objects.get(transaction_id=transaction_id)
                
                # Verify payment with Chapa
                chapa = ChapaService()
                verification_result = chapa.verify_payment(transaction_id)
                
                if verification_result['success']:
                    chapa_status = verification_result['status']
                    
                    if chapa_status == 'success':
                        payment.status = 'completed'
                        payment.paid_at = timezone.now()
                        payment.booking.status = 'confirmed'
                        payment.booking.save()
                        payment.verification_response = verification_result.get('response_data')
                        payment.save()
                        
                        logger.info("Payment completed via webhook", extra={
                            'payment_id': payment.id,
                            'booking_id': payment.booking.id,
                            'action': 'payment_completed_webhook'
                        })
                    
                    elif chapa_status in ['failed', 'cancelled']:
                        payment.status = 'failed'
                        payment.verification_response = verification_result.get('response_data')
                        payment.save()
                        
                        logger.warning("Payment failed via webhook", extra={
                            'payment_id': payment.id,
                            'status': chapa_status,
                            'action': 'payment_failed_webhook'
                        })
                
                else:
                    logger.error("Payment verification failed in webhook", extra={
                        'transaction_id': transaction_id,
                        'error': verification_result.get('message'),
                        'action': 'verification_failed_webhook'
                    })
            
            except Payment.DoesNotExist:
                logger.error("Payment not found for webhook", extra={
                    'transaction_id': transaction_id,
                    'action': 'payment_not_found_webhook'
                })
                return Response({'error': 'Payment not found'}, status=404)
            
            return Response({'status': 'webhook processed'})
            
        except Exception as e:
            logger.error("Unexpected error in webhook processing", extra={
                'error': str(e),
                'action': 'webhook_processing_error'
            })
            return Response({'error': 'Internal server error'}, status=500)

class PaymentSuccessView(APIView):
    """
    Success page after payment completion
    """
    def get(self, request):
        booking_id = request.GET.get('booking')
        transaction_id = request.GET.get('transaction_id')
        
        context = {
            'success': True,
            'message': 'Payment completed successfully!',
            'booking_id': booking_id,
            'transaction_id': transaction_id
        }
        
        logger.info("Payment success page accessed", extra={
            'booking_id': booking_id,
            'transaction_id': transaction_id,
            'action': 'payment_success_page'
        })
        
        return Response(context)