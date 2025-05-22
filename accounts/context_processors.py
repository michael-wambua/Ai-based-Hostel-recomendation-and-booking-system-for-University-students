def admin_counters(request):
    """Add counters for admin notifications."""
    context = {
        'pending_landlords_count': 0  # Default value
    }
    
    # Only query if user is an admin
    if request.user.is_authenticated and request.user.user_type == 'ADMIN':
        from accounts.models import LandlordProfile
        context['pending_landlords_count'] = LandlordProfile.objects.filter(
            verification_status='PENDING'
        ).count()
    
    return context