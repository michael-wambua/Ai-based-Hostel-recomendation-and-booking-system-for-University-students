from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.urls import reverse
from django.core.paginator import Paginator

from .models import Booking, BookingStatus, BookingRequest
from .forms import BookingForm, BookingCancellationForm, ExtendStayForm
from hostels.models import Hostel, Room
from accounts.models import User, LandlordProfile



# Student Views
@login_required
def student_bookings_dashboard(request):
    today = timezone.now().date()
    
    # Active bookings
    active_bookings = Booking.objects.filter(
        student=request.user,
        status=BookingStatus.CONFIRMED,
        end_date__gte=today
    ).select_related('room', 'room__hostel')
    
    # Calculate days remaining for each active booking
    for booking in active_bookings:
        booking.days_remaining = (booking.end_date - today).days
    
    # Past bookings
    past_bookings = Booking.objects.filter(
        student=request.user
    ).filter(
        Q(status=BookingStatus.COMPLETED) | 
        (Q(status=BookingStatus.CONFIRMED) & Q(end_date__lt=today))
    ).select_related('room', 'room__hostel')
    
    # Cancelled bookings
    cancelled_bookings = Booking.objects.filter(
        student=request.user,
        status=BookingStatus.CANCELLED
    ).select_related('room', 'room__hostel')
    
    return render(request, 'bookings/student/dashboard.html', {
        'active_bookings': active_bookings,
        'past_bookings': past_bookings,
        'cancelled_bookings': cancelled_bookings,
    })

def hostel_list(request):
    # Fetch all hostels from the database
    hostels = Hostel.objects.all()
    return render(request, 'bookings/student/dashboard.html', {
        'hostels': hostels,  
    })


@login_required
def book_hostel(request, hostel_id):
    hostel = get_object_or_404(Hostel, id=hostel_id)
    
    if request.method == 'POST':
        form = BookingForm(request.POST, student=request.user, hostel_id=hostel_id)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.student = request.user
            booking.status = BookingStatus.PENDING  # Ensure status is set to PENDING
            booking.booking_date = timezone.now()  # Set the booking date to current time
            booking.save()
            
            # Mark room as not available
            room = booking.room
            room.availability_status = True  # Use True instead of 'Available'  
            room.save()
            
            messages.success(request, "Your booking request has been submitted and is pending approval from the landlord")
        return redirect('bookings:student_dashboard')
    else:
        form = BookingForm(student=request.user, hostel_id=hostel_id)
    
    return render(request, 'bookings/student/book_hostel.html', {
        'form': form,
        'hostel': hostel,
    })

def booking_detail(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    return render(request, 'bookings/student/booking_detail.html', {'booking': booking})


@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, student=request.user)
    
    if not booking.is_active:
        messages.error(request, "You can only cancel active bookings.")
        return redirect('bookings:student_dashboard')
    
    if request.method == 'POST':
        form = BookingCancellationForm(request.POST)
        if form.is_valid():
            reason = form.cleaned_data['cancellation_reason']
            booking.cancel(reason)
            
            # Make the room available again
            room = booking.room
            room.availability_status = True  # Use True instead of 'Available'
            room.save()
            
            messages.success(request, "Your booking has been cancelled.")
            return redirect('bookings:student_dashboard')
    else:
        form = BookingCancellationForm()
    
    return render(request, 'bookings/student/cancel_booking.html', {
        'form': form,
        'booking': booking,
    })

@login_required
def booking_requests(request):
    # First check if the user is a landlord
    # This depends on how your user and landlord profile relationship is set up
    # Method 1: If LandlordProfile has a direct foreign key to User
    try:
        landlord_profile = LandlordProfile.objects.get(user=request.user)
    except LandlordProfile.DoesNotExist:
        messages.error(request, "You don't have access to this page. Only landlords can view booking requests.")
        return redirect('home')  # Redirect to home if not a landlord

    # Get all hostels owned by the landlord
    hostels = Hostel.objects.filter(owner=landlord_profile)

    # Get all rooms in these hostels
    rooms = Room.objects.filter(hostel__in=hostels)

    # Get pending booking requests for these rooms
    pending_bookings = Booking.objects.filter(
        room__in=rooms,
        status='pending'  # Use string value to match your model
    ).order_by('-booking_date')

    # Get recently processed bookings (approved or rejected)
    processed_bookings = Booking.objects.filter(
        room__in=rooms,
        status__in=['confirmed', 'rejected']  # Use string values to match your model
    ).order_by('-booking_date')[:10]

    pending_count = pending_bookings.count()

    return render(request, 'bookings/landlord/booking_requests.html', {
        'pending_bookings': pending_bookings,
        'processed_bookings': processed_bookings,
        'pending_count': pending_count
    })
@login_required
def approve_booking(request, booking_id):
    # Get the booking
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Check if the user is the owner of the hostel
    try:
        landlord_profile = LandlordProfile.objects.get(user=request.user)
        if booking.room.hostel.owner != landlord_profile:
            messages.error(request, "You don't have permission to approve this booking")
            return redirect('bookings:booking_requests')
    except LandlordProfile.DoesNotExist:
        messages.error(request, "You don't have permission to approve bookings")
        return redirect('home')
    
    # Update booking status
    booking.status = BookingStatus.CONFIRMED
    booking.save()
    
    # Mark the room as occupied/unavailable
    room = booking.room
    room.availability_status = False
    room.save()
    
    # Create an invoice for this booking
    from payments.models import Invoice
    
    # Calculate amount based on room price and booking duration
    if hasattr(room, 'price'):
        room_price = room.price
    else:
        # Default price if room doesn't have a price attribute
        room_price = 500  # Default value
    
    # Calculate number of days for the booking
    booking_days = (booking.end_date - booking.start_date).days
    total_amount = room_price * booking_days
    
    # Create the invoice
    invoice = Invoice.objects.create(
        booking=booking,
        amount=total_amount,
        # due_date is automatically set to 3 days from now in the model's save method
    )
    
    messages.success(request, f"Booking for {booking.student.get_full_name()} has been approved. An invoice has been generated.")
    return redirect('bookings:booking_requests')

@login_required
def reject_booking(request, booking_id):
    # Get the booking
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Check if the user is the owner of the hostel
    try:
        landlord_profile = LandlordProfile.objects.get(user=request.user)
        if booking.room.hostel.owner != landlord_profile:
            messages.error(request, "You don't have permission to reject this booking")
            return redirect('bookings:booking_requests')
    except LandlordProfile.DoesNotExist:
        messages.error(request, "You don't have permission to reject bookings")
        return redirect('home')
    
    # Update booking status
    booking.status = 'rejected'  # Use string value to match your model
    booking.save()
    
    # Ensure the room remains available for other bookings
    room = booking.room
    room.availability_status = True
    room.save()
    
    messages.success(request, f"Booking for {booking.student.get_full_name()} has been rejected")
    return redirect('bookings:booking_requests')

# Landlord Views
@login_required
def landlord_dashboard(request):
    # Check if user is a landlord
    if not hasattr(request.user, 'hostels'):
        messages.error(request, "You are not authorized to view this page.")
        return redirect('home')
    
    # Get all hostels owned by the landlord
    hostels = request.user.hostels.all()
    hostel_ids = hostels.values_list('id', flat=True)
    
    # Get all rooms in these hostels
    rooms = Room.objects.filter(hostel_id__in=hostel_ids)
    room_ids = rooms.values_list('id', flat=True)
    
    # Get all bookings for these rooms
    new_bookings = Booking.objects.filter(
        room_id__in=room_ids,
        status=BookingStatus.PENDING
    )
    
    active_bookings = Booking.objects.filter(
        room_id__in=room_ids,
        status=BookingStatus.CONFIRMED,
        end_date__gte=timezone.now().date()
    )
    
    cancelled_bookings = Booking.objects.filter(
        room_id__in=room_ids,
        status=BookingStatus.CANCELLED
    )
    
    past_bookings = Booking.objects.filter(
        Q(room_id__in=room_ids),
        Q(status=BookingStatus.COMPLETED) | 
        (Q(status=BookingStatus.CONFIRMED) & Q(end_date__lt=timezone.now().date()))
    )
    
    return render(request, 'bookings/landlord/dashboard.html', {
        'new_bookings': new_bookings,
        'active_bookings': active_bookings,
        'cancelled_bookings': cancelled_bookings,
        'past_bookings': past_bookings,
    })

# Admin Views
@login_required
def admin_bookings(request):
    # Check if user is admin
    if not request.user.is_staff:
        messages.error(request, "You are not authorized to view this page.")
        return redirect('home')
    
    all_bookings = Booking.objects.filter(
        status=BookingStatus.CONFIRMED,
        end_date__gte=timezone.now().date()
    )
    
    paginator = Paginator(all_bookings, 20)  # Show 20 bookings per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'bookings/admin/bookings_list.html', {
        'page_obj': page_obj,
    })

def terminate_booking(request, booking_id):
    # Logic to terminate booking
    if request.method == 'POST':
        reason = request.POST.get('reason')
        booking = get_object_or_404(Booking, id=booking_id)
        booking.status = 'Cancelled'
        booking.cancellation_reason = reason
        booking.cancelled_at = timezone.now()
        booking.save()
        
        # Update room availability
        room = booking.room
        room.availability_status = True  # Use True instead of 'Available'
        room.save()
        
        # Optionally notify student
        
        messages.success(request, f"Booking #{booking_id} has been terminated successfully.")
    return redirect('bookings:admin_bookings')

@login_required
def extend_stay(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, student=request.user)
    
    # Check if booking is active
    today = timezone.now().date()
    if booking.end_date < today:
        messages.error(request, "Cannot extend a completed booking")
        return redirect('bookings:booking_detail', booking_id=booking.id)
        
    if request.method == 'POST':
        form = ExtendStayForm(booking, request.POST)
        if form.is_valid():
            # Update the booking end date
            booking.end_date = form.cleaned_data['new_end_date']
            booking.save()
            
            messages.success(request, "Your stay has been successfully extended")
            return redirect('bookings:booking_detail', booking_id=booking.id)
    else:
        form = ExtendStayForm(booking)
    
    return render(request, 'bookings/student/extend_stay.html', {
        'booking': booking,
        'form': form
    })