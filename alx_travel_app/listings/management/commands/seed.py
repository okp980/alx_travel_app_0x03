# Seed the database with initial data
from django.core.management.base import BaseCommand
from listings.models import User, Listing, Review, Booking
import random
from faker import Faker

fake = Faker()
class Command(BaseCommand):
    help = 'Seed the database with initial data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding database...')
        self.seed_users(10)
        self.seed_listings(20)
        self.seed_reviews(50)
        self.seed_bookings(30)
        self.stdout.write('Database seeded!')

    def seed_users(self, count):
        for _ in range(count):
            User.objects.create(
                username=fake.user_name(),
                email=fake.email(),
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                role=random.choice(['host', 'guest', 'both']),
                password_hash=fake.password()
            )

    def seed_listings(self, count):
        users = User.objects.filter(role__in=['host', 'both'])
        property_types = ['apartment', 'house', 'condo', 'villa']
        amenities_list = ['wifi', 'kitchen', 'parking', 'pool', 'air_conditioning', 'heating', 'washer', 'dryer', 'tv', 'gym']
        random_descriptions = [
            "A beautiful place to stay with all the amenities you need.",
            "Cozy and comfortable, perfect for a weekend getaway.",
            "Luxurious accommodation with stunning views.",
            "Affordable and convenient, close to local attractions.",
            "Spacious and modern, ideal for families or groups."
        ]
        property_images = [
            'https://images.unsplash.com/photo-1522708323590-d24dbb6b0267',
            'https://images.unsplash.com/photo-1449158743715-0a90ebb6d2d8',
            'https://images.unsplash.com/photo-1518780664697-55e3ad937233',
            'https://images.unsplash.com/photo-1464822759849-e8e5f2f66ce0',
            'https://images.unsplash.com/photo-1568605114967-8130f3a36994',
            'https://images.unsplash.com/photo-1502672260266-1c1ef2d93688',
            'https://images.unsplash.com/photo-1487730116645-74489c95b41b',
            'https://images.unsplash.com/photo-1571896349842-33c89424de2d',
            'https://images.unsplash.com/photo-1520250497591-112f2f40a3f4',
            'https://images.unsplash.com/photo-1566073771259-6a8506099945'
        ]

        for _ in range(count):
            Listing.objects.create(
                host=random.choice(users),
                title=fake.sentence(nb_words=6),
                listing_image=random.choice(property_images),
                description=random.choice(random_descriptions),
                description_image=fake.image_url(),
                property_type=random.choice(property_types),
                amenities=random.sample(amenities_list, k=random.randint(2, 5)),
                address=fake.address(),
                price_per_night=round(random.uniform(50, 500), 2)
            )

    def seed_reviews(self, count):
        users = User.objects.all()
        listings = Listing.objects.all()
        for _ in range(count):
            Review.objects.create(
                listing=random.choice(listings),
                user=random.choice(users),
                rating=random.randint(1, 5),
                comment=fake.text()
            )

    def seed_bookings(self, count):
        users = User.objects.filter(role__in=['guest', 'both'])
        listings = Listing.objects.all()
        for _ in range(count):
            Booking.objects.create(
                # Don't allow hosts to book their own listings
                listing=random.choice([listing for listing in listings if listing.host not in users]),
                user=random.choice(users),
                start_date=fake.date_this_year(),
                end_date=fake.date_this_year(),
                total_price=round(random.uniform(100, 1000), 2),
            )