from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator

from hostels.models import Hostel

class UserManager(BaseUserManager):
    """Custom user manager for our custom user model."""
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user with the given email and password."""
        if not email:
            raise ValueError(_('The Email field must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', 'ADMIN')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom User model for authentication."""
    
    USER_TYPE_CHOICES = (
        ('STUDENT', 'Student'),
        ('LANDLORD', 'Landlord'),
        ('ADMIN', 'Administrator'),
    )
    
    username = None  # Remove username field
    email = models.EmailField(_('email address'), unique=True)
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True, null=True)
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='STUDENT')
    is_verified = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    shortlisted_hostels = models.ManyToManyField(
        'hostels.Hostel', 
        related_name='shortlisted_by',
        blank=True,
        verbose_name="Shortlisted Hostels"
    )
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    objects = UserManager()
    
    def __str__(self):
        return self.email
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class StudentProfile(models.Model):
    """Extended profile for students."""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    
    student_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    room = models.ForeignKey('hostels.Room', on_delete=models.SET_NULL, null=True, blank=True, related_name='student_occupants')    
    university = models.CharField(max_length=100, blank=True, null=True)
    course_of_study = models.CharField(max_length=100, blank=True, null=True)
    budget_min = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    budget_max = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    preferred_location = models.CharField(max_length=100, blank=True, null=True)

    ROOM_PREFERENCES = (
        ('SINGLE', 'Single Room'),
        ('DOUBLE', 'Double Room'),
        ('SHARED', 'Shared Room'),
        ('ANY', 'Any'),
    )
    
    room_preference = models.CharField(max_length=10, choices=ROOM_PREFERENCES, default='ANY')

    # Preferred amenities as comma-separated values
    preferred_amenities = models.TextField(blank=True, null=True)

    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
        ('N', 'Prefer not to say'),
    )
    
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)

    def __str__(self):
        return f"Profile for {self.user.email}"


class StudentPreference(models.Model):
    """Model for student housing preferences"""
    student = models.OneToOneField('StudentProfile', on_delete=models.CASCADE, related_name='preferences')
    budget_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    budget_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    
    ROOM_TYPE_CHOICES = (
        ('SINGLE', 'Single Room'),
        ('DOUBLE', 'Double Room'),
        ('SHARED', 'Shared Room'),
        ('ANY', 'Any'),
    )
    room_type = models.CharField(max_length=10, choices=ROOM_TYPE_CHOICES, default='ANY')
    amenities = models.ManyToManyField('hostels.Amenity', related_name='student_preferences', blank=True)
    
    def __str__(self):
        return f"Preferences for {self.student.user.email}"
    
    def get_room_type_display(self):
        """Return the display value for room_type"""
        for choice in self.ROOM_TYPE_CHOICES:
            if choice[0] == self.room_type:
                return choice[1]
        return "Not specified"

class LandlordProfile(models.Model):
    """Extended profile for landlords with verification attributes."""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='landlord_profile')
    hostel_name = models.CharField(max_length=100, blank=True, null=True)
    
    PROPERTY_TYPE_CHOICES = (
        ('OWNER', 'Owner'),
        ('MANAGER', 'Manager'),
        ('AGENT', 'Agent'),
    )
    
    property_ownership_type = models.CharField(max_length=10, choices=PROPERTY_TYPE_CHOICES, default='OWNER')
    
    # Additional fields for profile completeness
    bio = models.TextField(blank=True, null=True, help_text="Tell potential tenants about yourself and your property")
    years_of_experience = models.PositiveIntegerField(default=0, help_text="Years of experience in property management")
    
    # Contact preferences
    preferred_contact_method = models.CharField(
        max_length=10, 
        choices=(
            ('EMAIL', 'Email'),
            ('PHONE', 'Phone'),
            ('BOTH', 'Both Email and Phone'),
        ),
        default='BOTH'
    )
    available_hours = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        help_text="E.g. Weekdays 9AM-5PM"
    )
    
    # Verification documents
    id_document = models.FileField(upload_to='landlord/id_documents/', blank=True, null=True)
    property_proof = models.FileField(upload_to='landlord/property_proof/', blank=True, null=True)
    utility_bill = models.FileField(upload_to='landlord/utility_bills/', blank=True, null=True)

    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    
    # Verification status
    verification_status = models.CharField(
        max_length=10,
        choices=(
            ('PENDING', 'Pending'),
            ('APPROVED', 'Approved'),
            ('REJECTED', 'Rejected'),
        ),
        default='PENDING'
    )
    verification_notes = models.TextField(blank=True, null=True)
    verified_at = models.DateTimeField(blank=True, null=True)
    
    # Social media links
    facebook_link = models.URLField(blank=True, null=True)
    twitter_link = models.URLField(blank=True, null=True)
    instagram_link = models.URLField(blank=True, null=True)
    
    # Statistics (these could also be properties/methods)
    total_listings = models.PositiveIntegerField(default=0)
    total_bookings = models.PositiveIntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    
    def __str__(self):
        return f"Landlord: {self.user.email}"
    
    def is_verified(self):
        return self.verification_status == 'APPROVED'
    
    def update_statistics(self):
        """Update the statistics fields based on related data."""
        from django.db.models import Avg

        hostels = self.hostels.all()  # Use the property method

        self.total_listings = hostels.count()

        # Assuming you have a Booking model related to rooms
        self.total_bookings = sum(room.bookings.count() for hostel in hostels for room in hostel.rooms.all())

        # Assuming you have a Review model related to hostels with rating field
        ratings = [rating for hostel in hostels for rating in hostel.reviews.values_list('rating', flat=True)]
        
        if ratings:
            self.average_rating = sum(ratings) / len(ratings)

        self.save()

    
    # This will allow you to access hostels from a LandlordProfile
    @property
    def hostels(self):
        return Hostel.objects.filter(owner=self)