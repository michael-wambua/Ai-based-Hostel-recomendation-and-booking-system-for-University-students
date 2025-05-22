from django.db import models
from django.utils import timezone
from accounts.models import User
from hostels.models import Room, Hostel
from django.contrib.auth import get_user_model
from dateutil.relativedelta import relativedelta


class BookingStatus:
    PENDING = 'pending'
    CONFIRMED = 'confirmed'
    CANCELLED = 'cancelled'
    COMPLETED = 'completed'
    REJECTED = 'rejected'
    
    CHOICES = [
        (PENDING, 'Pending'),
        (CONFIRMED, 'Confirmed'),
        (CANCELLED, 'Cancelled'),
        (COMPLETED, 'Completed'),
        (REJECTED, 'Rejected'),
    ]

class Booking(models.Model):
    """Model for hostel room bookings"""
    student = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='bookings')
    room = models.ForeignKey('hostels.Room', on_delete=models.CASCADE, related_name='bookings')
    start_date = models.DateField()
    end_date = models.DateField()
    booking_date = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=20,
        choices=BookingStatus.CHOICES,
        default=BookingStatus.PENDING
    )
    cancellation_reason = models.TextField(blank=True, null=True)
    cancelled_at = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Booking #{self.id} - {self.student.username}"
    
    @property
    def is_active(self):
        return self.status == BookingStatus.CONFIRMED and self.end_date >= timezone.now().date()
    
    @property
    def is_pending(self):
        return self.status == BookingStatus.PENDING
    
    @property
    def check_in_date(self):
        return self.start_date

    @property
    def duration(self):
        """Returns number of months between start and end date."""
        delta = relativedelta(self.end_date, self.start_date)
        return delta.years * 12 + delta.months + (1 if delta.days > 0 else 0)

    @property
    def total_amount(self):
        """Calculate total cost based on room price and duration."""
        if self.room and self.room.price_per_month:
            return self.room.price_per_month * self.duration
        return 0

    def cancel(self, reason=None):
        self.status = BookingStatus.CANCELLED
        self.cancellation_reason = reason
        self.cancelled_at = timezone.now()
        self.save()
    
    def __str__(self):
        return f"{self.student.username} - {self.room} ({self.status})"

    class Meta:
        ordering = ['-booking_date']

class BookingRequest(models.Model):
    # Define fields for the BookingRequest model here
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')])
    date_requested = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Booking Request for {self.hostel.name} by {self.user.username}"