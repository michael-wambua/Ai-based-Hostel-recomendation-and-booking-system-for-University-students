from django.db import models
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
from bookings.models import Booking


class PaymentStatus:
    PENDING = 'pending'
    PAID = 'paid'
    CONFIRMED = 'confirmed'
    EXPIRED = 'expired'
    CANCELLED = 'cancelled'
    
    CHOICES = [
        (PENDING, 'Pending'),
        (PAID, 'Paid'),
        (CONFIRMED, 'Confirmed'),
        (EXPIRED, 'Expired'),
        (CANCELLED, 'Cancelled'),
    ]


class Invoice(models.Model):
    """Model for payment invoices"""
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='invoice')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.CHOICES,
        default=PaymentStatus.PENDING
    )
    
    def __str__(self):
        return f"Invoice #{self.id} for Booking #{self.booking.id}"
    
    def save(self, *args, **kwargs):
        # Set due date to 3 days from creation if it's a new invoice
        if not self.id and not self.due_date:
            self.due_date = timezone.now() + timedelta(days=3)
        super().save(*args, **kwargs)
    
    @property
    def is_overdue(self):
        return self.status == PaymentStatus.PENDING and timezone.now() > self.due_date
    
    @property
    def days_remaining(self):
        if self.status == PaymentStatus.PENDING:
            delta = self.due_date - timezone.now()
            return max(0, delta.days)
        return 0


class Payment(models.Model):
    """Model for payment records"""
    invoice = models.OneToOneField(Invoice, on_delete=models.CASCADE, related_name='payment')
    transaction_code = models.CharField(max_length=50)
    payment_date = models.DateTimeField(auto_now_add=True)
    confirmed_date = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='confirmed_payments'
    )
    payment_method = models.CharField(max_length=50, default='Bank Transfer')
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Payment for Invoice #{self.invoice.id}"
    
    def confirm_payment(self, user):
        self.confirmed_date = timezone.now()
        self.confirmed_by = user
        self.invoice.status = PaymentStatus.CONFIRMED
        self.invoice.save()
        self.save()