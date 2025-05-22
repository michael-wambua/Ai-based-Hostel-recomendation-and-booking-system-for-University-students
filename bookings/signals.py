from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Booking, BookingStatus

@receiver(post_save, sender=Booking)
def update_room_availability(sender, instance, created, **kwargs):
    """
    Signal to update room availability when a booking is created or updated
    """
    room = instance.room
    
    if instance.status == BookingStatus.CONFIRMED:
        room.is_available = False
    elif instance.status in [BookingStatus.CANCELLED, BookingStatus.COMPLETED]:
        # Check if there are any other active bookings for this room
        active_bookings = Booking.objects.filter(
            room=room,
            status=BookingStatus.CONFIRMED,
            end_date__gte=timezone.now().date()
        ).exclude(id=instance.id)
        
        if not active_bookings.exists():
            room.is_available = True
    
    room.save()
    