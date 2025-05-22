from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from .models import User, StudentProfile, LandlordProfile

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    """Create a profile when a user is created."""
    # Skip if the flag is set
    if hasattr(User, '_ignore_signals'):
        return
        
    if created:
        if instance.user_type == 'STUDENT':
            StudentProfile.objects.filter(user=instance).exists() or StudentProfile.objects.create(user=instance)
        elif instance.user_type == 'LANDLORD':
            LandlordProfile.objects.filter(user=instance).exists() or LandlordProfile.objects.create(user=instance)