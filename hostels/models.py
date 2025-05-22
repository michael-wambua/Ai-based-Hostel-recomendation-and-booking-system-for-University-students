from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
#from accounts.models import LandlordProfile, User

class Amenity(models.Model):
    """Model representing amenities available in hostels"""
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, blank=True, null=True, help_text="Font Awesome icon class")
    description = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name_plural = "Amenities"
        
    def __str__(self):
        return self.name

class Hostel(models.Model):
    """Model representing a hostel property"""
    
    owner = models.ForeignKey('accounts.LandlordProfile', on_delete=models.CASCADE, related_name='hostels')
    name = models.CharField(max_length=255)
    description = models.TextField()
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    distance_from_university = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        help_text="Distance in kilometers",
        null=True, 
        blank=True
    )
    university_name = models.CharField(max_length=255, blank=True, null=True)
    amenities = models.ManyToManyField(Amenity, related_name='hostels')
    rules = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    def get_average_rating(self):
        reviews = self.reviews.all()
        if reviews.exists():
            return reviews.aggregate(models.Avg('rating'))['rating__avg']
        return 0
    
    def get_rating_count(self):
        return self.reviews.count()
    
    def get_rating_distribution(self):
        """Returns the distribution of ratings (how many 5-star, 4-star, etc.)"""
        distribution = {
            5: self.reviews.filter(rating=5).count(),
            4: self.reviews.filter(rating=4).count(),
            3: self.reviews.filter(rating=3).count(),
            2: self.reviews.filter(rating=2).count(),
            1: self.reviews.filter(rating=1).count()
        }
        return distribution

class HostelImage(models.Model):
    """Model for storing hostel images"""
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='hostel_photos/')
    is_main = models.BooleanField(default=False)  # Flag for the main/featured image
    caption = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Image for {self.hostel.name}"

class RoomType(models.Model):
    """Model representing different types of rooms"""
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="room_types", null=True)
    name = models.CharField(max_length=100)  # e.g., Single, Double, Shared
    description = models.TextField(blank=True, null=True)
    capacity = models.PositiveIntegerField(default=1)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class Room(models.Model):
    """Model representing rooms within a hostel"""
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name='rooms')
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE, related_name='rooms')
    room_number = models.CharField(max_length=10, null=True)  # e.g., "101"
    description = models.TextField(blank=True, null=True)
    price_per_month = models.DecimalField(max_digits=10, decimal_places=2)
    security_deposit = models.DecimalField(max_digits=10, decimal_places=2)
    capacity = models.PositiveIntegerField()
    size = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        help_text="Size in square meters",
        null=True, 
        blank=True
    )
    availability_status = models.BooleanField(default=True)
    gender_restriction = models.CharField(
        max_length=10, 
        choices=[('male', 'Male Only'), ('female', 'Female Only'), ('any', 'Any')],
        default='any'
    )
    
    def __str__(self):
        return f"Room {self.room_number} at {self.hostel.name}"

class RoomImage(models.Model):
    """Model for storing room images"""
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='room_photos/')
    is_main = models.BooleanField(default=False)
    caption = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Image for {self.room.room_number}"

class Availability(models.Model):
    """Model for tracking room availability by date periods"""
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='availability_periods')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)  # Null means indefinite availability
    is_available = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.room.room_number} availability from {self.start_date}"
    
    class Meta:
        verbose_name_plural = "Availabilities"

class Review(models.Model):
    """Model for hostel reviews and ratings"""
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1-5 stars"
    )
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Review categories - Allow rating specific aspects
    cleanliness_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Cleanliness",
        null=True, blank=True
    )
    location_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Location",
        null=True, blank=True
    )
    value_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Value for Money",
        null=True, blank=True
    )
    facility_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Facilities",
        null=True, blank=True
    )
    
    # Verification that user has stayed at the hostel
    has_stayed = models.BooleanField(
        default=False,
        help_text="Indicates if the reviewer has stayed at the hostel"
    )
    booking = models.ForeignKey(
        'bookings.Booking',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        help_text="The related booking that verifies the stay"
    )
    
    class Meta:
        # Ensure a user can only review a hostel once
        unique_together = ('hostel', 'user')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Review for {self.hostel.name} by {self.user.username}"
    
    def get_average_category_rating(self):
        """Calculate average of all category ratings"""
        ratings = [r for r in [
            self.cleanliness_rating,
            self.location_rating,
            self.value_rating,
            self.facility_rating
        ] if r is not None]
        
        if ratings:
            return sum(ratings) / len(ratings)
        return self.rating  # Default to overall rating if no categories rated

class ReviewImage(models.Model):
    """Model for images associated with reviews"""
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='review_photos/')
    caption = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Image for review #{self.review.id}"

class ReviewReply(models.Model):
    """Model for landlord/owner replies to reviews"""
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='replies')
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Review Replies"
    
    def __str__(self):
        return f"Reply to review #{self.review.id}"
    
class SavedHostel(models.Model):
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name='saved_hostels')
    hostel = models.ForeignKey('hostels.Hostel', on_delete=models.CASCADE)
    saved_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'hostel')