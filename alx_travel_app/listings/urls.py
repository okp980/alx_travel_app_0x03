from django.urls import path
from .views import ListingViewSet, BookingViewSet, PaymentViewSet, ChapaWebhookView, PaymentSuccessView
from rest_framework.routers import DefaultRouter
from django.urls import include

router = DefaultRouter()
router.register(r'listings', ListingViewSet, basename='listing')
router.register(r'bookings', BookingViewSet, basename='booking')
router.register(r'payments', PaymentViewSet, basename='payment')

urlpatterns = [
    path('', include(router.urls)),
    path('chapa-webhook/', ChapaWebhookView.as_view(), name='chapa-webhook'),
    path('payment-success/', PaymentSuccessView.as_view(), name='payment-success'),
]