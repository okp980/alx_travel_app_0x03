from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid

# Create your models here.
# Using Django's ORM to define models for a travel application
# Users can list properties, leave reviews, and make bookings

USER_ROLES = (
    ('host', 'Host'),
    ('guest', 'Guest'),
    ('both', 'Both')
)

# Property type choices
PROPERTY_TYPES = (
    ('apartment', 'Apartment'),
    ('house', 'House'),
    ('villa', 'Villa'),
    ('cabin', 'Cabin'),
)

AMENITIES = (
    ('wifi', 'WiFi'),
    ('kitchen', 'Kitchen'),
    ('parking', 'Parking'),
    ('pool', 'Pool'),
    ('air_conditioning', 'Air Conditioning'),
    ('heating', 'Heating'),
    ('washer', 'Washer'),
    ('dryer', 'Dryer'),
    ('tv', 'TV'),
    ('gym', 'Gym'),
)

# User model
class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    role = models.CharField(max_length=10, choices=USER_ROLES, default='guest')
    password_hash = models.CharField(max_length=128)
    date_joined = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username

# Listing model
class Listing(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    host = models.ForeignKey(User, related_name='listings', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    listing_image = models.URLField(max_length=200, blank=True, null=True)
    description = models.TextField()
    description_image = models.URLField(max_length=200, blank=True, null=True)
    property_type = models.CharField(max_length=20, choices=PROPERTY_TYPES, default='apartment')
    amenities = models.JSONField(default=list)
    address = models.CharField(max_length=255)
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

# Review model
# Note: Each listing can have multiple reviews, but each review is linked to one listing and one user. Only users who have booked a listing can leave a review.
class Review(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(Listing, related_name='reviews', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='reviews', on_delete=models.CASCADE)
    rating = models.IntegerField()
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Review by {self.user} for {self.listing.title}'

# Booking model
class Booking(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(Listing, related_name='bookings', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='bookings', on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Booking by {self.user} for {self.listing.title} from {self.start_date} to {self.end_date}'
    
# Payment model
class Payment(models.Model):
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('canceled', 'Canceled'),
    ]
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="payment")
    transaction_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="NGN")
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    chapa_reference = models.CharField(max_length=100, blank=True, null=True)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    
    # Additional fields for tracking
    initiation_response = models.JSONField(blank=True, null=True)
    verification_response = models.JSONField(blank=True, null=True)
    
    def __str__(self):
        return f"Payment {self.transaction_id} - {self.status}"
    
    class Meta:
        ordering = ['-created_at']
