🏘️ ALX TRAVEL APP

This is a clone modeled after the AirBnB app

APPS CONTAINED

📋 Listings

This includes the Abstract User, Booking, Review and Listing models at the moment.

🛠️ Features include

👤 User: Central entity for both guests and hosts

id: PrimaryKey, AutoField, UUID.
username: unique
email: unique
first_name
last_name
role: user can be a guest, host or both
password_hash
date_joined
🏡 Listing: property hosted by user:

id: AutoField, PrimaryKey, UUID.
host: ForeignKey(User)
title: short catchy listing qualifier
listing_image: Major image advertising the booking
property type: Apartment, House, Villa, Cabin
description: descrition of the property
description_images: multiple images advertising listing
address
amenities
price_per_night
created_at
🛬 Booking: to link guest to listing for a specified period

id: AutoField, PrimaryKey, UUID.
guest: user making the booking, ForeignKey(User)
listing: property being booked. Made unavailable after booking confirmation. ForeignKey(Listing)
start_date
end_date
total_price
created_at
⭐️ Review: to gather guest feedback

id: AutoField, PrimaryKey, UUID.
listing: property being reviewed by user who had previously booked it.
author: guest making review
rating: ranging from one to five stars for the booking
comment: textfield for the author's review.