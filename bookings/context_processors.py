from bookings.models import Booking

def pending_bookings_count(request):
    """Context processor to add pending bookings count to all templates"""
    if request.user.is_authenticated and hasattr(request.user, 'landlord_profile'):
        # Count pending bookings for this landlord
        pending_count = Booking.objects.filter(
            room__hostel__owner=request.user.landlord_profile,
            status='pending'  # Adjust this to match your actual status value for pending
        ).count()
        return {'pending_count': pending_count}
    return {'pending_count': 0}