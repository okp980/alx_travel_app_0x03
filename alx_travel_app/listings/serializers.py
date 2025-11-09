# Serializers for Listing and Booking models
from rest_framework import serializers
from .models import Listing, Booking, Review, User, Payment

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'date_joined']

# Serializer for the Listing model
class ListingSerializer(serializers.ModelSerializer):
    host = UserSerializer()
    host_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), source='host', write_only=True)
    reviews = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Listing
        fields = ['host_id', 'host', 'title', 'listing_image', 'description', 'description_image', 'property_type', 'amenities', 'address', 'price_per_night', 'created_at', 'reviews']
        read_only_fields = ['id', 'created_at', 'reviews']

#Serializer for the Booking model
class BookingSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    user_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), source='user', write_only=True)
    listing = ListingSerializer()
    listing_id = serializers.PrimaryKeyRelatedField(queryset=Listing.objects.all(), source='listing', write_only=True)
    payment_status = serializers.CharField(source='payment.status', read_only=True, allow_null=True)
    payment_id = serializers.UUIDField(source='payment.id', read_only=True, allow_null=True)
    
    class Meta:
        model = Booking
        fields = ['id', 'listing_id', 'user_id', 'user', 'listing', 'start_date', 'end_date', 
                  'payment_status', 'payment_id', 'total_price', 'created_at']
        read_only_fields = ['id', 'user', 'total_price', 'created_at']


class PaymentInitiationSerializer(serializers.Serializer):
    booking_id = serializers.UUIDField(required=True)
    
    def validate_booking_id(self, value):
        """
        Validate that booking exists and belongs to user
        """
        from .models import Booking
        
        try:
            booking = Booking.objects.get(id=value)
            request = self.context.get('request')
            
            if booking.user != request.user and not request.user.is_staff:
                raise serializers.ValidationError("You do not have permission to pay for this booking.")
            
            # Check if payment already exists
            if hasattr(booking, 'payment'):
                raise serializers.ValidationError("Payment already exists for this booking.")
            
            return value
        except Booking.DoesNotExist:
            raise serializers.ValidationError("Booking not found.")

class PaymentSerializer(serializers.ModelSerializer):
    """
    Serializer for Payment model - Updated for UUID
    """
    booking_id = serializers.UUIDField(source='booking.id', read_only=True)
    booking_reference = serializers.UUIDField(source='booking.id', read_only=True)
    listing_title = serializers.CharField(source='booking.listing.title', read_only=True)
    user_email = serializers.CharField(source='booking.user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Payment
        fields = [
            'transaction_id', 'booking_id', 'booking_reference', 'transaction_id', 
            'amount', 'currency', 'status', 'chapa_reference', 'payment_method',
            'listing_title', 'user_email', 'user_name', 'created_at', 'updated_at', 'paid_at'
        ]
        read_only_fields = [
            'transaction_id', 'booking_id', 'booking_reference', 'transaction_id', 
            'amount', 'currency', 'chapa_reference', 'payment_method',
            'listing_title', 'user_email', 'user_name', 'created_at', 'updated_at', 'paid_at'
        ]
    
    def get_user_name(self, obj):
        """Get user's full name"""
        user = obj.booking.user
        return f"{user.first_name} {user.last_name}".strip() or user.email