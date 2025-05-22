import django
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg, Count
from django.core.paginator import Paginator
from django.urls import reverse
from django.http import HttpResponseForbidden, JsonResponse

from accounts.models import LandlordProfile
from bookings.models import Booking, BookingStatus
#from bookings.constants import BookingStatus

from .models import Hostel, HostelImage, Room, Amenity, RoomType, Review
from .forms import (
    HostelForm, RoomForm, HostelImageFormSet, RoomImageFormSet, 
    HostelSearchForm, AmenityForm, RoomTypeForm, Review, ReviewImageFormSet, ReviewForm,
    ReviewReplyForm
)

def hostel_list(request):
    """View for listing hostels with search and filtering"""
    
    # Initialize hostels before filtering
    hostels = Hostel.objects.all()

    search_form = HostelSearchForm(request.GET)
    
    # Apply filters if the form is valid
    if search_form.is_valid():
        data = search_form.cleaned_data
        
        # Search query (searches in name, description, and address)
        if data['search_query']:
            hostels = hostels.filter(
                Q(name__icontains=data['search_query']) |
                Q(description__icontains=data['search_query']) |
                Q(address__icontains=data['search_query'])
            )
        
        # University filter
        if data['university']:
            hostels = hostels.filter(university_name__icontains=data['university'])
        
        # City filter
        if data['city']:
            hostels = hostels.filter(city__icontains=data['city'])
        
        # Price range filter
        if data['min_price'] is not None or data['max_price'] is not None:
            # We need to filter rooms first and then get distinct hostels
            rooms_query = Room.objects.all()
            
            if data['min_price'] is not None:
                rooms_query = rooms_query.filter(price_per_month__gte=data['min_price'])
            
            if data['max_price'] is not None:
                rooms_query = rooms_query.filter(price_per_month__lte=data['max_price'])
                
            hostel_ids = rooms_query.values_list('hostel_id', flat=True).distinct()
            hostels = hostels.filter(id__in=hostel_ids)
        
        # Room type filter
        if data['room_type']:
            hostel_ids = Room.objects.filter(room_type=data['room_type']).values_list('hostel_id', flat=True).distinct()
            hostels = hostels.filter(id__in=hostel_ids)
        
        # Amenities filter
        if data['amenities']:
            for amenity in data['amenities']:
                hostels = hostels.filter(amenities=amenity)
        
        # Gender restriction filter
        if data['gender_restriction']:
            hostel_ids = Room.objects.filter(
                Q(gender_restriction=data['gender_restriction']) | 
                Q(gender_restriction='any')
            ).values_list('hostel_id', flat=True).distinct()
            hostels = hostels.filter(id__in=hostel_ids)
        
        # Distance filter
        if data['max_distance'] is not None:
            hostels = hostels.filter(distance_from_university__lte=data['max_distance'])
    
    # Make sure hostels always exists before annotation
    hostels = hostels.annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews')
    )

    # Paginate results
    paginator = Paginator(hostels, 10)  # Show 10 hostels per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_form': search_form,
        'amenities': Amenity.objects.all(),
        'room_types': RoomType.objects.all(),
    }
    return render(request, 'hostels/hostel_list.html', context)


def hostel_detail(request, hostel_id):
    """View for showing detailed information about a hostel"""
    hostel = get_object_or_404(Hostel.objects.select_related('owner'), id=hostel_id)

    # Check if the user is the owner
    is_owner = request.user.is_authenticated and hasattr(request.user, 'landlord_profile') and hostel.owner == request.user.landlord_profile

    # Allow everyone to view, but restrict actions
    can_edit = is_owner or request.user.is_staff  # Only owners and admins can edit/delete

    # Check if user can write a review
    can_write_review = request.user.is_authenticated and not (request.user.is_staff or is_owner)

    # Get all rooms for this hostel
    rooms = hostel.rooms.all()

    # Get all images for this hostel
    hostel_images = hostel.images.all()

    # Get main image for display, handle empty hostel_images
    main_image = hostel_images.filter(is_main=True).first()
    if not main_image:
        main_image = hostel_images.first()

    # Get hostel reviews (if any)
    reviews = hostel.reviews.prefetch_related('images', 'replies', 'user__profile').order_by('-created_at')[:5] if hasattr(hostel, 'reviews') else []

    user_review = None
    user_has_reviewed = False
    has_stayed = False
    can_review = False

    if request.user.is_authenticated:
        owner = hasattr(request.user, 'landlord_profile')
        is_admin = request.user.is_staff

        if not owner and not is_admin:
            has_stayed = Booking.objects.filter(student=request.user, room__hostel=hostel, status='completed').exists()
            user_review = Review.objects.filter(user=request.user, hostel=hostel).first()
            user_has_reviewed = user_review is not None
            can_review = has_stayed and not user_has_reviewed

    context = {
        'hostel': hostel,
        'rooms': rooms,
        'hostel_images': hostel_images,
        'main_image': main_image,
        'reviews': reviews,
        'can_edit': can_edit,  # Pass permission flag to template
        'user_review': user_review,
        'user_has_reviewed': user_has_reviewed,
        'has_stayed': has_stayed,
        'can_review': can_review,
        'is_owner': is_owner,
        'can_write_review': can_write_review
    }

    return render(request, 'hostels/hostel_detail.html', context)


def room_detail(request, hostel_id, room_id):
    """View for showing detailed information about a room"""
    hostel = get_object_or_404(Hostel, id=hostel_id)
    room = get_object_or_404(Room, id=room_id, hostel=hostel)

    # Get all images for this room
    room_images = room.images.all()

    # Get main image for display
    main_image = room_images.filter(is_main=True).first() or room_images.first()

    context = {
        'hostel': hostel,
        'room': room,
        'room_images': room_images,
        'main_image': main_image,
    }
    return render(request, 'hostels/room_detail.html', context)


@login_required
def add_hostel(request):
    if request.method == 'POST':
        form = HostelForm(request.POST)
        
        if form.is_valid():
            # Save the hostel instance without committing to the database immediately
            hostel = form.save(commit=False)

            # Assign the current logged-in user as the owner
            hostel.owner = request.user.landlord_profile  # Assuming 'owner' is a ForeignKey to User

            # Save the hostel first
            hostel.save()

            # Manually handle amenities, since the landlord enters them as a comma-separated string
            amenities_list = form.cleaned_data['amenities'].split(',')
            for amenity_name in amenities_list:
                amenity_name = amenity_name.strip()  # Remove leading/trailing spaces
                if amenity_name:  # Ensure it's not an empty string
                    # Get or create Amenity objects
                    amenity_obj, created = Amenity.objects.get_or_create(name=amenity_name)
                    hostel.amenities.add(amenity_obj)

            # Now that amenities have been added, commit the hostel instance
            hostel.save()

            # Handle hostel images (if any)
            image_formset = HostelImageFormSet(request.POST, request.FILES, instance=hostel)
            if image_formset.is_valid():
                image_formset.save()

            # Redirect to a success page or hostel list page
            return redirect('landlord_hostels')

    else:
        # Create empty forms for GET request
        form = HostelForm()
        image_formset = HostelImageFormSet(queryset=HostelImage.objects.none())

    return render(request, 'hostels/hostel_form.html', {'form': form, 'image_formset': image_formset})

@login_required
def edit_hostel(request, hostel_id):
    """View for editing an existing hostel"""
    hostel = get_object_or_404(Hostel, id=hostel_id)
    
    # Check if user is the owner of this hostel
    if hostel.owner != request.user.landlord_profile and not request.user.is_staff:
        messages.error(request, "You don't have permission to edit this hostel.")
        return redirect('hostel_detail', hostel_id=hostel.id)
    
    if request.method == 'POST':
        # print("POST Data:", request.POST)
        # print("Files Data:", request.FILES)

        form = HostelForm(request.POST, request.FILES, instance=hostel)
        image_formset = HostelImageFormSet(request.POST, request.FILES, instance=hostel)
        
        if form.is_valid() and image_formset.is_valid():
            updated_hostel = form.save(commit=False)
            updated_hostel.save()
            image_formset.save()

            messages.success(request, "Hostel details updated successfully.")
            return redirect('hostel_detail', hostel_id=updated_hostel.id)
    else:
        form = HostelForm(instance=hostel)
        image_formset = HostelImageFormSet(instance=hostel)
    
    context = {
        'form': form,
        'image_formset': image_formset,
        'hostel': hostel,
        'title': 'Edit Hostel'
    }
    return render(request, 'hostels/hostel_form.html', context)


@login_required
def add_room(request, hostel_id):
    """View for adding a new room to a hostel"""
    hostel = get_object_or_404(Hostel, id=hostel_id)
    
    # Check if user is the owner of this hostel
    if hostel.owner != request.user.landlord_profile and not request.user.is_staff:
        messages.error(request, "You don't have permission to add rooms to this hostel.")
        return redirect('hostel_detail', hostel_id=hostel.id)
    
    if request.method == 'POST':
        form = RoomForm(request.POST)
        image_formset = RoomImageFormSet(request.POST, request.FILES)
        
        if form.is_valid():
            if image_formset.is_valid():
                # Save room but don't commit to DB yet
                room = form.save(commit=False)
                room.hostel = hostel
                room.save()
                
                # Save images
                image_formset.instance = room
                image_formset.save()
                
                messages.success(request, "Room added successfully.")
                return redirect('room_list', hostel_id=hostel.id)
            else:
                # Add image formset errors to messages
                for form_idx, form_errors in enumerate(image_formset.errors):
                    for field, errors in form_errors.items():
                        for error in errors:
                            messages.error(request, f"Image {form_idx+1} {field}: {error}")
                print("Image formset errors:", image_formset.errors)
        else:
            # Add form errors to messages
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            print("Form errors:", form.errors)
    else:
        form = RoomForm()
        image_formset = RoomImageFormSet()
    
    context = {
        'form': form,
        'image_formset': image_formset,
        'hostel': hostel,
        'title': 'Add New Room'
    }
    return render(request, 'hostels/room_form.html', context)

@login_required
def edit_room(request, hostel_id, room_id):
    """View for editing an existing room"""
    hostel = get_object_or_404(Hostel, id=hostel_id)
    room = get_object_or_404(Room, id=room_id, hostel=hostel)
    
    # Check if user is the owner of this hostel
    if hostel.owner != request.user.landlord_profile and not request.user.is_staff:
        messages.error(request, "You don't have permission to edit this room.")
        return redirect('room_detail', hostel_id=hostel.id, room_id=room.id)
    
    if request.method == 'POST':
        form = RoomForm(request.POST, instance=room)
        image_formset = RoomImageFormSet(request.POST, request.FILES, instance=room)
        
        if form.is_valid() and image_formset.is_valid():
            # Save room
            room = form.save()
            
            # Save images
            image_formset.save()
            
            messages.success(request, "Room details updated successfully.")
            return redirect('room_detail', hostel_id=hostel.id, room_id=room.id)
    else:
        form = RoomForm(instance=room)
        image_formset = RoomImageFormSet(instance=room)
    
    context = {
        'form': form,
        'image_formset': image_formset,
        'hostel': hostel,
        'room': room,
        'title': 'Edit Room'
    }
    return render(request, 'hostels/room_form.html', context)

def room_list(request, hostel_id):
    """View for listing all rooms of a specific hostel"""
    hostel = get_object_or_404(Hostel, id=hostel_id)
    
    # Get all rooms for this hostel
    rooms = hostel.rooms.all()
    
    # Check if user is the owner to show additional controls
    is_owner = False
    if request.user.is_authenticated:
        if hasattr(request.user, 'landlord_profile') and hostel.owner == request.user.landlord_profile:
            is_owner = True
        elif request.user.is_staff:
            is_owner = True
    
    context = {
        'hostel': hostel,
        'rooms': rooms,
        'is_owner': is_owner,
        'title': f'Rooms at {hostel.name}'
    }
    return render(request, 'hostels/room_list.html', context)

@login_required
def delete_hostel(request, hostel_id):
    """View for deleting a hostel"""
    hostel = get_object_or_404(Hostel, id=hostel_id)
    
    # Check if user is the owner of this hostel or admin
    if hostel.owner != request.user.landlord_profile and not request.user.is_staff:
        messages.error(request, "You don't have permission to delete this hostel.")
        return redirect('hostel_detail', hostel_id=hostel.id)
    
    if request.method == 'POST':
        hostel.delete()
        messages.success(request, "Hostel deleted successfully.")
        return redirect('landlord_hostels')
    
    context = {
        'hostel': hostel,
    }
    return render(request, 'hostels/delete_hostel.html', context)

@login_required
def delete_room(request, hostel_id, room_id):
    """View for deleting a room"""
    hostel = get_object_or_404(Hostel, id=hostel_id)
    room = get_object_or_404(Room, id=room_id, hostel=hostel)
    
    # Check if user is the owner of this hostel or admin
    if hostel.owner != request.user.landlord_profile and not request.user.is_staff:
        messages.error(request, "You don't have permission to delete this room.")
        return redirect('room_detail', hostel_id=hostel.id, room_id=room.id)
    
    if request.method == 'POST':
        room.delete()
        messages.success(request, "Room deleted successfully.")
        return redirect('hostel_detail', hostel_id=hostel.id)
    
    context = {
        'hostel': hostel,
        'room': room,
    }
    return render(request, 'hostels/delete_room.html', context)

@login_required
def landlord_hostels(request):
    """View for landlords (and admins) to see all their hostels"""
    user = request.user

    # Allow superusers or staff users to view all hostels
    if user.is_superuser or user.is_staff:
        hostels = Hostel.objects.all()
    else:
        try:
            landlord_profile = user.landlord_profile
        except LandlordProfile.DoesNotExist:
            messages.error(request, "Only landlords or admins can access this page.")
            return redirect('dashboard')

        hostels = Hostel.objects.filter(owner=landlord_profile)

        if not hostels.exists():
            messages.info(request, "You don't have any hostels yet.")
            return redirect('add_hostel')

    context = {
        'hostels': hostels,
    }
    return render(request, 'hostels/landlord_hostels.html', context)

@login_required
def landlord_tenants(request):
    """View for landlord to see all tenants who have booked their hostels"""
    
    # Get the landlord profile
    landlord_profile = request.user.landlord_profile
    
    # Get all hostels owned by this landlord
    hostels = Hostel.objects.filter(owner=landlord_profile)
    
    # Get confirmed bookings for these hostels
    bookings = Booking.objects.filter(
        room__hostel__in=hostels,
        status=BookingStatus.CONFIRMED
    ).select_related('student', 'room', 'room__hostel')
    
    # Organize bookings by hostel
    tenants_by_hostel = {}
    for hostel in hostels:
        hostel_bookings = [b for b in bookings if b.room.hostel.id == hostel.id]
        tenants_by_hostel[hostel] = hostel_bookings
    
    context = {
        'tenants_by_hostel': tenants_by_hostel,
    }
    
    return render(request, 'hostels/tenants.html', context)

@login_required
def toggle_room_availability(request, room_id):
    """AJAX view to toggle room availability status"""
    if not request.user.is_landlord:
        return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
    
    room = get_object_or_404(Room, id=room_id)
    
    # Check if user owns the hostel containing this room
    if room.hostel.owner != request.user:
        return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
    
    # Toggle the availability status
    room.availability_status = not room.availability_status
    room.save()
    
    return JsonResponse({
        'status': 'success',
        'availability': room.availability_status
    })

@login_required
def compare_hostels(request):
    """View for comparing multiple hostels"""
    hostel_ids = request.GET.getlist('hostel_id')
    
    if not hostel_ids:
        messages.warning(request, "Please select at least one hostel to compare.")
        return redirect('hostel_list')
    
    hostels = Hostel.objects.filter(id__in=hostel_ids)
    
    # Get all amenities for these hostels
    all_amenities = set()
    for hostel in hostels:
        all_amenities.update(hostel.amenities.all())
    
    context = {
        'hostels': hostels,
        'all_amenities': all_amenities,
    }
    return render(request, 'hostels/compare_hostels.html', context)

@login_required
def add_amenity(request):
    """View for landlord to add new amenities"""
    # Check if user is a landlord
    if not hasattr(request.user, 'landlord_profile'):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('home')
    
    if request.method == 'POST':
        form = AmenityForm(request.POST)
        if form.is_valid():
            amenity = form.save(commit=False)
            amenity.owner = request.user.landlord_profile
            amenity.save()
            messages.success(request, "New amenity added successfully.")
            return redirect('amenity_list')
    else:
        form = AmenityForm()
    
    context = {
        'form': form,
        'title': 'Add New Amenity'
    }
    return render(request, 'hostels/amenity_form.html', context)

@login_required
def amenity_list(request):
    """View for landlord to manage amenities"""
    # Check if user is a landlord
    if not hasattr(request.user, 'landlord_profile'):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('home')
    
    # Get only the amenities associated with this landlord
    amenities = Amenity.objects.filter(owner=request.user.landlord_profile)
    
    context = {
        'amenities': amenities,
    }
    return render(request, 'hostels/amenity_list.html', context)

@login_required
def add_room_type(request):
    """View for landlord to add new room types"""
    # Check if user is a landlord
    if not hasattr(request.user, 'landlord_profile'):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('home')
    
    # Get the landlord's hostel or handle multiple hostels if applicable
    try:
        #hostel = request.user.landlord_profile.hostel  # Assuming a one-to-one relationship
        # If you have a many-to-many relationship, you might need to:
        # 1. First get the hostel ID from the request
        hostel_id = request.GET.get('hostel_id')
        hostel = request.user.landlord_profile.hostels.get(id=hostel_id)
    except:
        messages.error(request, "No hostel found. Please create a hostel first.")
        return redirect('add_hostel')  # Redirect to hostel creation
    
    if request.method == 'POST':
        form = RoomTypeForm(request.POST)
        if form.is_valid():
            room_type = form.save(commit=False)
            room_type.hostel = hostel  # Set the hostel relation
            room_type.save()
            messages.success(request, "New room type added successfully.")
            return redirect('room_type_list')
    else:
        form = RoomTypeForm()
    
    context = {
        'form': form,
        'title': 'Add New Room Type',
        'hostel': hostel  # Pass hostel to the template if needed
    }
    return render(request, 'hostels/room_type_form.html', context)

@login_required
def edit_room_type(request, hostel_id, room_type_id):
    """View for landlord to edit a room type"""
    try:
        hostel = request.user.landlord_profile.hostels.get(id=hostel_id)
        room_type = hostel.room_types.get(id=room_type_id)
    except (Hostel.DoesNotExist, RoomType.DoesNotExist):
        messages.error(request, "Hostel or Room Type not found.")
        return redirect('room_type_list', hostel_id=hostel_id)
    
    if request.method == 'POST':
        form = RoomTypeForm(request.POST, instance=room_type)
        if form.is_valid():
            form.save()
            messages.success(request, "Room type updated successfully.")
            return redirect('room_type_list', hostel_id=hostel.id)
    else:
        form = RoomTypeForm(instance=room_type)

    context = {
        'form': form,
        'title': 'Edit Room Type',
        'hostel': hostel,
        'room_type': room_type
    }
    return render(request, 'hostels/room_type_form.html', context)


@login_required
def room_type_list(request):
    """View for landlord to manage room types"""
    if not hasattr(request.user, 'landlord_profile'):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('home')

    landlord_profile = request.user.landlord_profile

    # Ensure filtering is done with LandlordProfile, not User
    hostels = Hostel.objects.filter(owner=landlord_profile)

    # Get room types for those hostels
    room_types = RoomType.objects.filter(hostel__in=hostels)

    # Debugging: Log the room types to check if they are correctly filtered
    print(f"Room Types: {room_types}")

    context = {
        'room_types': room_types,
    }

    return render(request, 'hostels/room_type_list.html', context)


@login_required
def user_shortlist(request):
    """View for students to see their shortlisted hostels"""
    # Check if user is a landlord and redirect them
    if hasattr(request.user, 'landlordprofile'):
        messages.warning(request, "This feature is for student users only.")
        return redirect('landlord_dashboard')

    # This requires a ManyToMany relationship between User and Hostel for shortlisting
    shortlisted_hostels = request.user.shortlisted_hostels.all()
    
    # Annotate with ratings for consistency with hostel_list view
    shortlisted_hostels = shortlisted_hostels.annotate(
        avg_rating=django.db.models.Avg('reviews__rating'),
        review_count=django.db.models.Count('reviews')
    )

    context = {
        'shortlisted_hostels': shortlisted_hostels,
    }

    return render(request, 'hostels/user_shortlist.html', context)

from django.db.models import Avg, Count

@login_required
def toggle_shortlist(request):
    """AJAX view to add/remove a hostel from user's shortlist"""
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        hostel_id = request.POST.get('hostel_id')
        hostel = get_object_or_404(Hostel, id=hostel_id)

        # Check if hostel is already in shortlist
        if hostel in request.user.shortlisted_hostels.all():
            request.user.shortlisted_hostels.remove(hostel)
            is_shortlisted = False
            message = "Removed from shortlist"
        else:
            request.user.shortlisted_hostels.add(hostel)
            is_shortlisted = True
            message = "Added to shortlist"

        # Get the updated shortlisted hostels with annotations for avg_rating and review_count
        shortlisted_hostels = request.user.shortlisted_hostels.annotate(
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews')
        )

        # Get the new shortlisted count
        shortlisted_count = request.user.shortlisted_hostels.count()

        # Return the updated count and status
        return JsonResponse({
            'status': 'success',
            'is_shortlisted': is_shortlisted,
            'message': message,
            'new_shortlisted_count': shortlisted_count,
            'shortlisted_hostels': [
                {
                    'id': h.id,
                    'name': h.name,
                    'avg_rating': h.avg_rating,  # Now you can access avg_rating
                    'review_count': h.review_count
                } for h in shortlisted_hostels
            ],
        })

    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)


@login_required
def get_shortlisted_count(request):
    """Return the count of shortlisted hostels for the logged-in user."""
    if request.user.user_type != 'STUDENT':
        return JsonResponse({'status': 'error', 'message': 'Access denied'}, status=403)

    shortlisted_count = request.user.shortlisted_hostels.count()
    
    return JsonResponse({
        'status': 'success',
        'shortlisted_count': shortlisted_count
    })

@login_required
def remove_shortlist(request):
    """AJAX view to remove a hostel from user's shortlist"""
    if request.method == 'POST':
        hostel_id = request.POST.get('hostel_id')
        if hostel_id:
            try:
                hostel = Hostel.objects.get(id=hostel_id)
                # Remove the hostel from the user's shortlist
                request.user.shortlisted_hostels.remove(hostel)

                # Update the session with the new shortlisted hostels count
                shortlisted_hostels = request.user.shortlisted_hostels.all()
                request.session['shortlisted_hostels'] = [hostel.id for hostel in shortlisted_hostels]

                # Send the updated count back as a response
                return JsonResponse({
                    'status': 'success',
                    'message': 'Hostel removed from shortlist.',
                    'new_count': len(shortlisted_hostels)
                })
            except Hostel.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Hostel not found.'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Hostel ID is missing.'})
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})


@login_required
def add_review(request, hostel_id):
    """Add a new review for a hostel"""
    hostel = get_object_or_404(Hostel, id=hostel_id)
    
    # Check if user has already reviewed this hostel
    existing_review = Review.objects.filter(hostel=hostel, user=request.user).first()
    if existing_review:
        messages.warning(request, "You have already reviewed this hostel. You can edit your existing review.")
        return redirect('edit_review', review_id=existing_review.id)
    
    # Check if user has stayed at this hostel
    has_stayed = Booking.objects.filter(
        student=request.user,
        room__hostel=hostel,
        status='completed'  # Assuming 'completed' is the status for finished stays
    ).exists()
    
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        formset = ReviewImageFormSet(request.POST, request.FILES)
        
        if form.is_valid() and formset.is_valid():
            review = form.save(commit=False)
            review.hostel = hostel
            review.user = request.user
            review.has_stayed = has_stayed
            
            # If user has a booking, associate it with the review
            if has_stayed:
                booking = Booking.objects.filter(
                    user=request.user, 
                    room__hostel=hostel,
                    status='completed'
                ).order_by('-checkout_date').first()
                review.booking = booking
                
            review.save()
            
            # Save the images
            formset.instance = review
            formset.save()
            
            messages.success(request, "Your review has been submitted successfully!")
            return redirect('hostel_detail', hostel_id=hostel.id)
    else:
        form = ReviewForm()
        formset = ReviewImageFormSet()
    
    context = {
        'form': form,
        'formset': formset,
        'hostel': hostel,
        'has_stayed': has_stayed
    }
    return render(request, 'hostels/add_review.html', context)

@login_required
def edit_review(request, review_id):
    """Edit an existing review"""
    review = get_object_or_404(Review, id=review_id)
    
    # Check if the user is the author of the review
    if review.user != request.user:
        return HttpResponseForbidden("You cannot edit someone else's review.")
    
    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=review)
        formset = ReviewImageFormSet(request.POST, request.FILES, instance=review)
        
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, "Your review has been updated successfully!")
            return redirect('hostel_detail', hostel_id=review.hostel.id)
    else:
        form = ReviewForm(instance=review)
        formset = ReviewImageFormSet(instance=review)
    
    context = {
        'form': form,
        'formset': formset,
        'review': review,
        'hostel': review.hostel
    }
    return render(request, 'hostels/edit_review.html', context)

@login_required
def delete_review(request, review_id):
    """Delete a review"""
    review = get_object_or_404(Review, id=review_id)
    
    # Check if the user is the author of the review
    if review.user != request.user:
        return HttpResponseForbidden("You cannot delete someone else's review.")
    
    hostel_id = review.hostel.id
    
    if request.method == 'POST':
        review.delete()
        messages.success(request, "Your review has been deleted.")
        return redirect('hostel_detail', hostel_id=hostel_id)
    
    context = {
        'review': review,
        'hostel': review.hostel
    }
    return render(request, 'hostels/delete_review_confirm.html', context)

@login_required
def add_review_reply(request, review_id):
    """Add a reply to a review (for landlords/owners)"""
    review = get_object_or_404(Review, id=review_id)
    hostel = review.hostel

    # ✅ Fix: use `.all()` to iterate
    if hostel not in request.user.landlord_profile.hostels.all() and not request.user.is_staff:
        return HttpResponseForbidden("Only the hostel owner can reply to reviews.")
    
    if request.method == 'POST':
        form = ReviewReplyForm(request.POST)
        
        if form.is_valid():
            reply = form.save(commit=False)
            reply.review = review
            reply.user = request.user
            reply.save()
            
            messages.success(request, "Your reply has been posted.")
            return redirect('hostel_detail', hostel_id=hostel.id)
    else:
        form = ReviewReplyForm()
    
    context = {
        'form': form,
        'review': review,
        'hostel': hostel
    }
    return render(request, 'hostels/add_review_reply.html', context)


def hostel_reviews(request, hostel_id):
    """View all reviews for a specific hostel"""
    hostel = get_object_or_404(Hostel, id=hostel_id)
    reviews = hostel.reviews.all().order_by('-created_at')

    # Fetch the landlord profile for each review user if they have one
    landlord_profiles = {}
    for review in reviews:
        try:
            # Safely check if the user has a landlord profile
            landlord_profiles[review.id] = review.user.landlord_profile
        except LandlordProfile.DoesNotExist:
            landlord_profiles[review.id] = None

    # Filter options
    rating_filter = request.GET.get('rating', None)
    if rating_filter:
        reviews = reviews.filter(rating=rating_filter)

    # Sort options
    sort = request.GET.get('sort', 'recent')
    if sort == 'highest':
        reviews = reviews.order_by('-rating', '-created_at')
    elif sort == 'lowest':
        reviews = reviews.order_by('rating', '-created_at')

    # Check if the user is the owner of this hostel
    is_owner = False
    if request.user.is_authenticated and hasattr(request.user, 'landlord_profile'):
        is_owner = request.user.landlord_profile.hostels.filter(id=hostel.id).exists()
    
    main_image = hostel.images.filter(is_main=True).first()
    if not main_image:
        main_image = hostel.images.first()

    context = {
        'hostel': hostel,
        'reviews': reviews,
        'rating_distribution': hostel.get_rating_distribution(),
        'average_rating': hostel.get_average_rating(),
        'review_count': hostel.get_rating_count(),
        'current_filter': rating_filter,
        'current_sort': sort,
        'is_owner': is_owner,
        'main_image': main_image,
        'landlord_profiles': landlord_profiles  # Pass the landlord profiles
    }

    return render(request, 'hostels/hostel_reviews.html', context)

@login_required
def export_tenants_excel(request):
    """Export tenants list to Excel file"""
    # Create a workbook and add a worksheet
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    
    # Add bold format for headers
    header_format = workbook.add_format({
        'bold': True,
        'border': 1,
        'bg_color': '#F0F0F0',
        'text_wrap': True,
        'valign': 'vcenter',
        'align': 'center',
    })
    
    # Add date format
    date_format = workbook.add_format({'num_format': 'mmm d yyyy'})
    
    # Get landlord's hostels with prefetched bookings
    landlord = request.user.landlord_profile
    hostels = Hostel.objects.filter(owner=landlord).prefetch_related(
        Prefetch('rooms__bookings', queryset=Booking.objects.select_related('student', 'room'))
    )
    
    for hostel in hostels:
        # Create worksheet for each hostel
        worksheet = workbook.add_worksheet(hostel.name[:31])  # Excel worksheet names limited to 31 chars
        
        # Set column widths
        worksheet.set_column('A:A', 30)  # Tenant name
        worksheet.set_column('B:B', 15)  # Room number
        worksheet.set_column('C:D', 15)  # Dates
        worksheet.set_column('E:E', 25)  # Email
        worksheet.set_column('F:F', 15)  # Phone
        
        # Write headers
        headers = ['Tenant', 'Room', 'Start Date', 'End Date', 'Email', 'Phone']
        for col_num, header in enumerate(headers):
            worksheet.write(0, col_num, header, header_format)
        
        # Write data rows
        row = 1
        for room in hostel.rooms.all():
            for booking in room.bookings.all():
                worksheet.write(row, 0, booking.student.get_full_name())
                worksheet.write(row, 1, room.room_number)
                worksheet.write(row, 2, booking.start_date, date_format)
                worksheet.write(row, 3, booking.end_date, date_format)
                worksheet.write(row, 4, booking.student.email)
                worksheet.write(row, 5, booking.student.phone_number or "N/A")
                row += 1
    
    # Close the workbook before sending the data
    workbook.close()
    
    # Rewind the buffer
    output.seek(0)
    
    # Set up the Http response
    filename = f"tenants_list_{datetime.now().strftime('%Y%m%d')}.xlsx"
    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response

@login_required
def export_tenants_pdf(request):
    """Export tenants list to PDF file"""
    # Create a file-like buffer to receive PDF data
    buffer = BytesIO()
    
    # Create the PDF object using the buffer as its "file"
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=landscape(letter),
        rightMargin=72, 
        leftMargin=72,
        topMargin=72, 
        bottomMargin=72
    )
    
    # Get landlord's hostels with prefetched bookings
    landlord = request.user.landlord_profile
    hostels = Hostel.objects.filter(owner=landlord).prefetch_related(
        Prefetch('rooms__bookings', queryset=Booking.objects.select_related('student', 'room'))
    )
    
    # Container for the 'Story' (sequence of flowables)
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    subtitle_style = styles['Heading2']
    normal_style = styles['Normal']
    
    # Add heading
    elements.append(Paragraph("Tenant List", title_style))
    elements.append(Paragraph(f"Generated on {datetime.now().strftime('%B %d, %Y')}", normal_style))
    elements.append(Spacer(1, 0.5*inch))
    
    # Process each hostel
    for hostel in hostels:
        # Add hostel name as subtitle
        elements.append(Paragraph(f"Property: {hostel.name}", subtitle_style))
        elements.append(Paragraph(f"Address: {hostel.address}, {hostel.city}", normal_style))
        elements.append(Spacer(1, 0.25*inch))
        
        # Collect booking data for this hostel
        booking_data = []
        
        # Table headers
        headers = ['Tenant', 'Room', 'Start Date', 'End Date', 'Email', 'Phone']
        booking_data.append(headers)
        
        # Add data rows
        for room in hostel.rooms.all():
            for booking in room.bookings.all():
                row = [
                    booking.student.get_full_name(),
                    room.room_number,
                    booking.start_date.strftime('%b %d, %Y'),
                    booking.end_date.strftime('%b %d, %Y'),
                    booking.student.email,
                    booking.student.phone_number or "N/A"
                ]
                booking_data.append(row)
        
        # Create table for this hostel
        if len(booking_data) > 1:  # If there are any bookings
            table = Table(booking_data, repeatRows=1)
            
            # Add table style
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ]))
            
            elements.append(table)
        else:
            # No bookings message
            elements.append(Paragraph("No tenants for this property.", normal_style))
        
        elements.append(Spacer(1, 0.5*inch))
    
    # Build the PDF
    doc.build(elements)
    
    # Get the value of the buffer
    pdf = buffer.getvalue()
    buffer.close()
    
    # Create the HTTP response
    filename = f"tenants_list_{datetime.now().strftime('%Y%m%d')}.pdf"
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write(pdf)
    
    return response
