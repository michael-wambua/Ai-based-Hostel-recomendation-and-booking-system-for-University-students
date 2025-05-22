from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import DetailView, UpdateView, ListView, DeleteView, CreateView
from django.urls import reverse_lazy, reverse
from django.views import View
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from decimal import Decimal
from django.db.models import Q
from django.http import HttpResponse
from django.db.models import Prefetch
import xlwt
from hostels.forms import HostelForm
from hostels.models import Hostel, Room, SavedHostel
from bookings.models import Booking
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import models
from datetime import timedelta
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseRedirect
from hostels.models import Hostel, Room, Review
from bookings.models import Booking, BookingStatus, BookingRequest
from payments.models import Invoice, Payment, PaymentStatus
from io import BytesIO
import xlsxwriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from datetime import datetime
from .forms import (
    UserLoginForm, StudentRegistrationForm, LandlordRegistrationForm,
    StudentProfileForm, LandlordProfileForm, VerificationDocumentsForm, 
    UserProfileForm, ProfilePictureForm, StudentPreferenceForm, LandlordForm,
    StudentCreationForm
)
from .models import User, StudentProfile, LandlordProfile, StudentPreference


def login_view(request):
    """Custom login view that checks verification status."""
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            user = authenticate(request, username=email, password=password)
            
            if user is not None:
                # Check if user is a landlord and if verified
                if user.user_type == 'LANDLORD' and not user.is_verified:
                    messages.warning(
                        request, 
                        "Your landlord account is pending verification. We'll notify you once it's approved."
                    )
                    return redirect('login')
                
                # If we get here, user can be logged in
                login(request, user)
                
                # Redirect based on 'next' parameter or to dashboard
                if 'next' in request.POST and request.POST.get('next'):
                    return redirect(request.POST.get('next'))
                else:
                    return redirect('dashboard')
            else:
                messages.error(request, "Invalid email or password.")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{error}")
    else:
        form = UserLoginForm()
        
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    """Handle user logout."""
    logout(request)
    messages.success(request, "You have been logged out successfully!")
    return redirect('home')

def register_student(request):
    """Handle student registration."""
    if request.user.is_authenticated:
        return redirect('login')
    
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Login the user after successful registration
            login(request, user)
            messages.success(request, "Registration successful! Welcome to Hostel Finder!")
            return redirect('student_profile_setup')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = StudentRegistrationForm()
    
    return render(request, 'accounts/register_student.html', {'form': form})


def register_landlord(request):
    """Handle landlord registration with document verification."""
    if request.user.is_authenticated:
        return redirect('home')  # Changed from 'landlord_verification_pending'
    
    if request.method == 'POST':
        form = LandlordRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            # Remove the login(request, user) line
            
            # Notify admin about new landlord registration
            try:
                admin_emails = User.objects.filter(user_type='ADMIN').values_list('email', flat=True)
                if admin_emails:
                    send_mail(
                        subject="New Landlord Registration Requires Verification",
                        message=f"A new landlord ({user.email}) has registered and needs verification.",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=list(admin_emails),
                        fail_silently=True
                    )
            except Exception as e:
                # Log the error but continue with the registration process
                print(f"Error sending notification email: {str(e)}")
                
            messages.success(
                request, 
                "Registration successful! Your account is pending verification. "
                "We'll notify you once it's approved."
            )
            # Redirect to a public page that explains verification is pending
            return redirect('landlord_registration_success')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = LandlordRegistrationForm()
    
    return render(request, 'accounts/register_landlord.html', {'form': form})


def landlord_registration_success(request):
    """Public view shown after landlord registers successfully."""
    return render(request, 'accounts/landlord_registration_success.html')

@login_required
def dashboard(request):
    """Main dashboard view - redirects based on user type."""
    user = request.user
    
    if user.user_type == 'STUDENT':
        return redirect('student_dashboard')
    elif user.user_type == 'LANDLORD':
        if not user.is_verified:
            return redirect('landlord_verification_pending')
        return redirect('landlord_dashboard')
    elif user.user_type == 'ADMIN':
        return redirect('admin_dashboard')
    else:
        # Fallback
        messages.warning(request, "User type not recognized.")
        return redirect('home')

@login_required
def student_dashboard(request):
    """Dashboard view for students."""
    if request.user.user_type != 'STUDENT':
        messages.warning(request, "Access denied. Student privileges required.")
        return redirect('dashboard')
    
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)
    
    # Check if preferences exist
    try:
        preferences = StudentPreference.objects.get(student=profile)
        has_preferences = True
    except StudentPreference.DoesNotExist:
        preferences = None
        has_preferences = False
    
    today = timezone.now().date()
    
    # Use case-insensitive lookup for the status field
    recent_bookings = request.user.bookings.filter(
        status__iexact='CONFIRMED',  # Case-insensitive match
        end_date__gte=today
    ).select_related('room', 'room__hostel')
    
    # Calculate days remaining for each active booking
    for booking in recent_bookings:
        booking.days_remaining = (booking.end_date - today).days
    
    # Get all shortlisted hostels
    saved_hostels = request.user.shortlisted_hostels.all()
    
    # Fetch recommended hostels based on preferences
    recommended_hostels = []
    if has_preferences:
        # Get all hostels first
        all_hostels = Hostel.objects.all()
        
        # Calculate match scores for each hostel
        scored_hostels = []
        
        for hostel in all_hostels:
            # Initialize base score
            match_score = Decimal('0')
            total_weight = Decimal('0')
            match_reasons = []
            
            # Check price match (weight: 30)
            weight = Decimal('30')
            total_weight += weight
            
            # Get the lowest priced room in this hostel
            min_price_room = hostel.room_types.aggregate(min_price=models.Min('base_price'))['min_price']
            max_price_room = hostel.room_types.aggregate(max_price=models.Max('base_price'))['max_price']
            
            if min_price_room and max_price_room and preferences.budget_min and preferences.budget_max:
                # Price overlap calculation
                if max_price_room >= preferences.budget_min and min_price_room <= preferences.budget_max:
                    price_overlap = min(max_price_room, preferences.budget_max) - max(min_price_room, preferences.budget_min)
                    price_range = preferences.budget_max - preferences.budget_min
                    
                    if price_range > 0:
                        price_score = (price_overlap / price_range) * weight
                        match_score += price_score
                        if price_score > weight * Decimal('0.7'):
                            match_reasons.append("Price matches your budget well")
            
            # Check location match (weight: 25)
            weight = Decimal('25')
            total_weight += weight
            
            if preferences.location and hostel.address:
                # Simple string matching for now - could be enhanced with geographic data
                if preferences.location.lower() in hostel.address.lower():
                    match_score += weight
                    match_reasons.append(f"Located in your preferred area: {preferences.location}")
            
            # Check room type match (weight: 20)
            weight = Decimal('20')
            total_weight += weight
            
            if preferences.room_type and preferences.room_type != 'ANY':
                if hostel.room_types.filter(name__icontains=preferences.room_type).exists():
                    match_score += weight
                    match_reasons.append(f"Has your preferred {preferences.get_room_type_display()} available")
            else:
                # If no preference, give partial points
                match_score += weight * Decimal('0.5')
            
            # Check amenities match (weight: 25)
            weight = Decimal('25')
            total_weight += weight
            
            preferred_amenities = list(preferences.amenities.all())
            if preferred_amenities:
                hostel_amenities = hostel.amenities.all()
                
                # Calculate percentage of matched amenities
                matched_amenities = []
                for amenity in preferred_amenities:
                    if amenity in hostel_amenities:
                        matched_amenities.append(amenity)
                
                if preferred_amenities:
                    amenity_match_percentage = Decimal(len(matched_amenities)) / Decimal(len(preferred_amenities))
                    amenity_score = amenity_match_percentage * weight
                    match_score += amenity_score
                    
                    if matched_amenities:
                        amenity_names = ", ".join([a.name for a in matched_amenities[:3]])
                        if len(matched_amenities) > 3:
                            amenity_names += f" and {len(matched_amenities) - 3} more"
                        match_reasons.append(f"Includes amenities: {amenity_names}")
            
            # Calculate final percentage
            if total_weight > 0:
                final_score = int((match_score / total_weight) * 100)
            else:
                final_score = 0
            
            # Add available rooms count
            available_rooms = hostel.room_types.filter(is_active=True).count()
            
            # Add information to the hostel object
            hostel.match_score = final_score
            hostel.match_reasons = match_reasons[:3]  # Top 3 reasons
            hostel.available_rooms = available_rooms
            hostel.price_per_month = min_price_room  # Use minimum price as display price
            
            scored_hostels.append(hostel)
        
        # Sort by match score (descending)
        recommended_hostels = sorted(scored_hostels, key=lambda x: x.match_score, reverse=True)[:5]
    
    context = {
        'profile': profile,
        'student': profile,  # For template compatibility
        'saved_hostels': saved_hostels,
        'recent_bookings': recent_bookings,
        'recommended_hostels': recommended_hostels,
        'today': today,
    }
    return render(request, 'accounts/student_dashboard.html', context)

@login_required
def update_preferences(request):
    """Update student housing preferences"""
    if request.user.user_type != 'STUDENT':
        messages.warning(request, "Access denied. Student privileges required.")
        return redirect('dashboard')
    
    profile = StudentProfile.objects.get(user=request.user)
    preferences, created = StudentPreference.objects.get_or_create(student=profile)
    
    if request.method == 'POST':
        form = StudentPreferenceForm(request.POST, instance=preferences)
        if form.is_valid():
            form.save()
            messages.success(request, "Your housing preferences have been updated successfully!")
            return redirect('student_dashboard')
    else:
        form = StudentPreferenceForm(instance=preferences)
    
    context = {
        'form': form,
    }
    
    return render(request, 'accounts/update_preferences.html', context)

@login_required
def all_recommendations(request):
    """View all recommended hostels"""
    if request.user.user_type != 'STUDENT':
        messages.warning(request, "Access denied. Student privileges required.")
        return redirect('dashboard')
    
    profile = StudentProfile.objects.get(user=request.user)
    
    # Check if preferences exist
    try:
        preferences = StudentPreference.objects.get(student=profile)
        has_preferences = True
    except StudentPreference.DoesNotExist:
        preferences = None
        has_preferences = False
    
    # Use the same recommendation logic as in student_dashboard
    # But don't limit the results
    recommended_hostels = []
    
    # [Insert the same recommendation algorithm as in student_dashboard]
    # But remove the [:5] limit at the end
    
    context = {
        'recommended_hostels': recommended_hostels,
        'has_preferences': has_preferences
    }
    
    return render(request, 'accounts/all_recommendations.html', context)

def recommendation_explanation(request):
    """Explains how the recommendation algorithm works"""
    return render(request, 'accounts/recommendation_explanation.html')


@login_required
def landlord_dashboard(request):
    """Dashboard view for verified landlords."""
    if request.user.user_type != 'LANDLORD' or not request.user.is_verified:
        messages.warning(request, "Access denied. Verified landlord privileges required.")
        return redirect('dashboard')
    
    # Get current date for display
    today = timezone.now()
    
    # Get landlord profile
    profile = request.user.landlord_profile
    
    # Get landlord's hostels
    hostels = Hostel.objects.filter(owner=profile)
    
    # Calculate room statistics
    hostel_ids = hostels.values_list('id', flat=True)
    total_rooms = Room.objects.filter(hostel__in=hostel_ids).count()
    
    # Get room IDs for this landlord
    room_ids = Room.objects.filter(hostel__in=hostel_ids).values_list('id', flat=True)
    
    # Calculate active bookings (occupied rooms)
    occupied_rooms = Booking.objects.filter(
        room__id__in=room_ids,
        status=BookingStatus.CONFIRMED,
        start_date__lte=today,
        end_date__gte=today
    ).count()
    
    # Calculate vacant rooms
    vacant_rooms = total_rooms - occupied_rooms
    
    # Calculate occupancy percentage
    occupied_percentage = 0
    if total_rooms > 0:
        occupied_percentage = round((occupied_rooms / total_rooms) * 100)
    
    # Get current tenants with their room and hostel information
    # We need to make sure we're prefetching all the related data needed by the template
    current_tenants = User.objects.filter(
        bookings__room__hostel__in=hostels,
        bookings__status=BookingStatus.CONFIRMED,
        bookings__end_date__gte=today
    ).select_related(
        'student_profile',  # Prefetch student profile
    ).prefetch_related(
        'bookings',  # Prefetch bookings for end_date calculation
        'student_profile__room',  # Prefetch room
        'student_profile__room__hostel',  # Prefetch hostel
    ).distinct()
    
    # Ensure student profiles have the room information set
    # This might be necessary if the data model relationship isn't already defined
    for tenant in current_tenants:
        # Get the latest active booking for this tenant
        active_booking = tenant.bookings.filter(
            status=BookingStatus.CONFIRMED,
            end_date__gte=today
        ).order_by('-start_date').first()
        
        # If there's an active booking, make sure the student profile has the room reference
        if active_booking and hasattr(tenant, 'student_profile'):
            # This assumes you either have a direct reference or need to set it
            tenant.student_profile.room = active_booking.room
    
    total_tenants = current_tenants.count()
    
    # Rest of the code remains the same...
    # Get recent payment information
    recent_payments = Payment.objects.filter(
        invoice__booking__room__hostel__in=hostels
    ).order_by('-payment_date')[:5]
    
    # Calculate total income
    total_income = Payment.objects.filter(
        invoice__booking__room__hostel__in=hostels,
        invoice__status=PaymentStatus.CONFIRMED
    ).aggregate(total=models.Sum('invoice__amount'))['total'] or 0
    
    # Get count of pending payments
    pending_payments_count = Invoice.objects.filter(
        booking__room__hostel__in=hostels,
        status=PaymentStatus.PENDING
    ).count()
    
    # Get new booking requests
    new_booking_requests = Booking.objects.filter(
        room__hostel__in=hostels,
        status=BookingStatus.PENDING  # Use the PENDING constant from your BookingStatus class
    ).order_by('-booking_date')[:5]
    
    # Get ratings and reviews
    latest_reviews = Review.objects.filter(
        hostel__in=hostels
    ).order_by('-created_at')[:5]
    
    total_reviews = Review.objects.filter(hostel__in=hostels).count()
    
    # Calculate average rating
    average_rating = 0
    if total_reviews > 0:
        average_rating = Review.objects.filter(
            hostel__in=hostels
        ).aggregate(avg=models.Avg('rating'))['avg'] or 0
    
    # Mock activity logs
    activity_logs = [
        {
            'timestamp': timezone.now() - timedelta(hours=2),
            'message': 'You replied to a review for Hostel Sunshine',
            'color': 'success'
        },
        {
            'timestamp': timezone.now() - timedelta(days=1),
            'message': 'New booking request received for Room 203',
            'color': 'warning'
        },
        {
            'timestamp': timezone.now() - timedelta(days=2),
            'message': 'Payment confirmed for Booking #1023',
            'color': 'info'
        }
    ]
    
    context = {
        'today': today,
        'profile': profile,
        'hostels': hostels,
        'total_rooms': total_rooms,
        'occupied_percentage': occupied_percentage,
        'vacant_rooms': vacant_rooms,
        'current_tenants': current_tenants,
        'total_tenants': total_tenants,
        'recent_payments': recent_payments,
        'total_income': total_income,
        'pending_payments_count': pending_payments_count,
        'new_booking_requests': new_booking_requests,
        'latest_reviews': latest_reviews,
        'average_rating': average_rating,
        'total_reviews': total_reviews,
        'activity_logs': activity_logs,
    }
    
    return render(request, 'accounts/landlord_dashboard.html', context)


@login_required
def admin_dashboard(request):
    """Dashboard view for admin users."""
    if request.user.user_type != 'ADMIN':
        messages.warning(request, "Access denied. Admin privileges required.")
        return redirect('dashboard')
    
    # Get pending verifications
    pending_verifications = LandlordProfile.objects.filter(verification_status='PENDING').count()
    
    # Get basic stats (to be expanded later)
    students_count = User.objects.filter(user_type='STUDENT').count()
    landlords_count = User.objects.filter(user_type='LANDLORD').count()
    verified_landlords = User.objects.filter(user_type='LANDLORD', is_verified=True).count()
    
    # Get hostel count
    hostels_count = Hostel.objects.count()
    
    context = {
        'pending_verifications': pending_verifications,
        'students_count': students_count,
        'landlords_count': landlords_count,
        'verified_landlords': verified_landlords,
        'hostels_count': hostels_count,
    }
    
    return render(request, 'accounts/admin/dashboard.html', context)

# Admin student management views
class AdminUserPassesTestMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.user_type == 'ADMIN'

class AdminStudentListView(LoginRequiredMixin, AdminUserPassesTestMixin, ListView):
    model = User
    template_name = 'accounts/admin/student_list.html'
    context_object_name = 'students'
    paginate_by = 10  # Add pagination
    
    def get_queryset(self):
        queryset = User.objects.filter(user_type='STUDENT')
        
        # Get search query
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(first_name__icontains=query) | 
                Q(last_name__icontains=query) | 
                Q(email__icontains=query)
            )
        
        return queryset.order_by('-date_joined')

class AdminStudentCreateView(LoginRequiredMixin, AdminUserPassesTestMixin, CreateView):
    """View for creating a new student"""
    model = User
    form_class = StudentCreationForm
    template_name = 'accounts/admin/student_form.html'
    success_url = reverse_lazy('student_list')
    
    def form_valid(self, form):
        # Set user type to STUDENT
        user = form.save(commit=False)
        user.user_type = 'STUDENT'
        user.save()
        
        # Create empty student profile
        StudentProfile.objects.create(user=user)
        
        messages.success(self.request, f"Student {user.email} has been created successfully!")
        return super().form_valid(form)

class AdminStudentDetailView(LoginRequiredMixin, AdminUserPassesTestMixin, DetailView):
    model = User
    template_name = 'accounts/admin/student_detail.html'
    context_object_name = 'student'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.get_object()
        try:
            context['profile'] = student.student_profile 
        except StudentProfile.DoesNotExist:
            context['profile'] = None
        return context

class AdminStudentUpdateView(LoginRequiredMixin, AdminUserPassesTestMixin, UpdateView):
    model = User
    template_name = 'accounts/admin/student_update.html'
    fields = ['first_name', 'last_name', 'email', 'is_active']
    
    def get_success_url(self):
        return reverse_lazy('student_detail', kwargs={'pk': self.object.pk})

class AdminStudentDeleteView(LoginRequiredMixin, AdminUserPassesTestMixin, DeleteView):
    model = User
    template_name = 'accounts/admin/student_delete.html'
    success_url = reverse_lazy('student_list')
    
    def get_queryset(self):
        return User.objects.filter(user_type='STUDENT')


def export_students_excel(request):
    """Export students data to Excel"""
    if request.user.user_type != 'ADMIN':
        messages.warning(request, "Access denied. Admin privileges required.")
        return redirect('dashboard')
        
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename="students.xls"'

    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Students')

    # Sheet header, first row
    row_num = 0

    font_style = xlwt.XFStyle()
    font_style.font.bold = True

    columns = ['ID', 'First Name', 'Last Name', 'Email', 'Student ID', 'University', 'Course']

    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num], font_style)

    # Sheet body, remaining rows
    font_style = xlwt.XFStyle()

    students = User.objects.filter(user_type='STUDENT')
    
    for student in students:
        row_num += 1
        ws.write(row_num, 0, student.id, font_style)
        ws.write(row_num, 1, student.first_name, font_style)
        ws.write(row_num, 2, student.last_name, font_style)
        ws.write(row_num, 3, student.email, font_style)
        
        # Try to get profile data
        try:
            profile = student.student_profile
            ws.write(row_num, 4, profile.student_id or '', font_style)
            ws.write(row_num, 5, profile.university or '', font_style)
            ws.write(row_num, 6, profile.course_of_study or '', font_style)
        except:
            ws.write(row_num, 4, '', font_style)
            ws.write(row_num, 5, '', font_style)
            ws.write(row_num, 6, '', font_style)

    wb.save(response)
    return response

def export_students_pdf(request):
    """Export students data to PDF"""
    if request.user.user_type != 'ADMIN':
        messages.warning(request, "Access denied. Admin privileges required.")
        return redirect('dashboard')
        
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="students.pdf"'

    # Create the PDF object using reportlab
    doc = SimpleDocTemplate(response, pagesize=letter)
    elements = []
    
    styles = getSampleStyleSheet()
    elements.append(Paragraph('Student List', styles['Heading1']))
    elements.append(Paragraph(f'Generated on {datetime.now().strftime("%Y-%m-%d %H:%M")}', styles['Normal']))
    
    # Add student data
    data = [['ID', 'Name', 'Email', 'Student ID', 'University', 'Course']]
    
    students = User.objects.filter(user_type='STUDENT')
    
    for student in students:
        try:
            profile = student.student_profile
            data.append([
                str(student.id),
                f"{student.first_name} {student.last_name}",
                student.email,
                profile.student_id or '',
                profile.university or '',
                profile.course_of_study or ''
            ])
        except:
            data.append([
                str(student.id),
                f"{student.first_name} {student.last_name}",
                student.email,
                '', '', ''
            ])
    
    # Create the table
    t = Table(data)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(t)
    doc.build(elements)
    
    return response

# Admin Hostel Management
@login_required
def admin_hostel_list(request):
    """View for admin to see all hostels."""
    if request.user.user_type != 'ADMIN':
        messages.warning(request, "Access denied. Admin privileges required.")
        return redirect('dashboard')
    
    hostels = Hostel.objects.all().order_by('-created_at')
    total_hostels = hostels.count()
    
    context = {
        'hostels': hostels,
        'total_hostels': total_hostels
    }
    
    return render(request, 'accounts/admin/hostel_list.html', context)

@login_required
def admin_hostel_detail(request, pk):
    """View for admin to see details of a specific hostel."""
    if request.user.user_type != 'ADMIN':
        messages.warning(request, "Access denied. Admin privileges required.")
        return redirect('dashboard')
    
    hostel = get_object_or_404(Hostel, pk=pk)
    rooms = hostel.rooms.all()
    
    context = {
        'hostel': hostel,
        'rooms': rooms
    }
    
    return render(request, 'accounts/admin/hostel_detail.html', context)

@login_required
def admin_hostel_create(request):
    """View for admin to create a hostel for a landlord."""
    if request.user.user_type != 'ADMIN':
        messages.warning(request, "Access denied. Admin privileges required.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = HostelForm(request.POST)
        if form.is_valid():
            hostel = form.save(commit=False)
            # Get the landlord selected in the form
            landlord_id = request.POST.get('landlord')
            landlord = get_object_or_404(LandlordProfile, pk=landlord_id)
            hostel.owner = landlord
            hostel.save()
            #form.save_m2m()  # Save many-to-many relationships
            messages.success(request, "Hostel created successfully!")
            return redirect('admin_hostel_list')
    else:
        form = HostelForm()
        # Also get list of landlords for the dropdown
        landlords = LandlordProfile.objects.filter(user__is_verified=True)
    
    context = {
        'form': form,
        'landlords': landlords
    }
    
    return render(request, 'accounts/admin/hostel_create.html', context)

@login_required
def admin_hostel_update(request, pk):
    """View for admin to update a hostel."""
    if request.user.user_type != 'ADMIN':
        messages.warning(request, "Access denied. Admin privileges required.")
        return redirect('dashboard')
    
    hostel = get_object_or_404(Hostel, pk=pk)
    
    if request.method == 'POST':
        form = HostelForm(request.POST, instance=hostel)
        if form.is_valid():
            form.save()
            messages.success(request, "Hostel updated successfully!")
            return redirect('admin_hostel_detail', pk=hostel.pk)
    else:
        form = HostelForm(instance=hostel)
    
    context = {
        'form': form,
        'hostel': hostel
    }
    
    return render(request, 'accounts/admin/hostel_update.html', context)

@login_required
def admin_hostel_delete(request, pk):
    """View for admin to delete a hostel."""
    if request.user.user_type != 'ADMIN':
        messages.warning(request, "Access denied. Admin privileges required.")
        return redirect('dashboard')
    
    hostel = get_object_or_404(Hostel, pk=pk)
    
    if request.method == 'POST':
        hostel_name = hostel.name
        hostel.delete()
        messages.success(request, f"Hostel '{hostel_name}' deleted successfully!")
        return redirect('admin_hostel_list')
    
    context = {
        'hostel': hostel
    }
    
    return render(request, 'accounts/admin/hostel_delete.html', context)


@login_required
def student_profile_setup(request):
    """Handle student profile setup after registration."""
    if request.user.user_type != 'STUDENT':
        messages.warning(request, "This page is only for students.")
        return redirect('dashboard')

    # Get the profile (it should already exist from form.save())
    try:
        profile = StudentProfile.objects.get(user=request.user)
    except StudentProfile.DoesNotExist:
        profile = StudentProfile.objects.create(user=request.user)

    if request.method == 'POST':
        form = StudentProfileForm(request.POST, request.FILES, instance=profile)  # Accepting files
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('student_dashboard')
    else:
        form = StudentProfileForm(instance=profile)

    return render(request, 'accounts/student_profile_setup.html', {'form': form})

@method_decorator(login_required, name='dispatch')
class StudentProfileView(DetailView):
    """View for displaying a student's profile."""
    model = StudentProfile
    template_name = 'accounts/student_profile.html'
    context_object_name = 'profile'
    
    def get_object(self):
        return get_object_or_404(StudentProfile, user=self.request.user)


@method_decorator(login_required, name='dispatch')
class StudentProfileUpdateView(UpdateView):
    """View for updating a student's profile."""
    model = StudentProfile
    form_class = StudentProfileForm
    template_name = 'accounts/student_profile_update.html'
    success_url = reverse_lazy('student_profile')

    def get_object(self):
        return get_object_or_404(StudentProfile, user=self.request.user)

    def form_valid(self, form):
        profile = form.save(commit=False)
        # Handle profile picture update explicitly
        if 'profile_picture' in self.request.FILES:
            profile.profile_picture = self.request.FILES['profile_picture']
        profile.save()
        messages.success(self.request, "Profile updated successfully!")
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class LandlordProfileView(DetailView):
    """View for displaying a landlord's profile."""
    model = LandlordProfile
    template_name = 'accounts/landlord_profile.html'
    context_object_name = 'profile'
    
    def get_object(self):
        return get_object_or_404(LandlordProfile, user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        landlord_profile = getattr(self.request.user, 'landlordprofile', None)
        
        if landlord_profile:
            context['hostels'] = landlord_profile.hostels.all()
        else:
            context['hostels'] = []  # Or some other default behavior
        
        # Update statistics before displaying
        profile = self.get_object()
        profile.update_statistics()
        
        return context

    
    def dispatch(self, request, *args, **kwargs):
        if request.user.user_type != 'LANDLORD':
            messages.warning(request, "Access denied. Landlord privileges required.")
            return redirect('dashboard')
        if not request.user.is_verified and 'profile' not in request.path:
            return redirect('landlord_registration_success')
        return super().dispatch(request, *args, **kwargs)


@method_decorator(login_required, name='dispatch')
class LandlordProfileUpdateView(UpdateView):
    """View for updating a landlord's profile."""
    model = LandlordProfile
    form_class = LandlordProfileForm
    template_name = 'accounts/landlord_profile_update.html'
    success_url = reverse_lazy('landlord_profile')
    
    def get_object(self):
        profile = get_object_or_404(LandlordProfile, user=self.request.user)
        print(profile)  # This will print the profile data in the console
        return profile

    def form_valid(self, form):
        profile = form.save(commit=False)
        # Handle profile picture update
        if 'profile_picture' in self.request.FILES:
            profile.profile_picture = self.request.FILES['profile_picture']
        profile.save()
        messages.success(self.request, "Profile updated successfully!")
        return super().form_valid(form)
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.user_type != 'LANDLORD':
            messages.warning(request, "Access denied. Landlord privileges required.")
            return redirect('dashboard')
        if not request.user.is_verified:
            messages.warning(request, "Your account needs verification before you can update your profile.")
            return redirect('landlord_registration_success')
        return super().dispatch(request, *args, **kwargs)


@method_decorator(login_required, name='dispatch')
class UpdatePersonalInfoView(UpdateView):
    """View for updating user's personal information."""
    model = LandlordProfile
    form_class = UserProfileForm
    template_name = 'accounts/update_personal_info.html'
    success_url = reverse_lazy('landlord_profile')
    
    def get_object(self):
        return get_object_or_404(LandlordProfile, user=self.request.user)
    
    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Personal information updated successfully!")
        return super().form_valid(form)
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.user_type != 'LANDLORD':
            messages.warning(request, "Access denied. Landlord privileges required.")
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)


@method_decorator(login_required, name='dispatch')
class UpdateProfilePictureView(UpdateView):
    """View for updating user's profile picture."""
    model = LandlordProfile
    form_class = ProfilePictureForm
    template_name = 'accounts/update_profile_picture.html'
    success_url = reverse_lazy('landlord_profile')
    
    def get_object(self):
        return get_object_or_404(LandlordProfile, user=self.request.user)
    
    def form_valid(self, form):
        user = form.save(commit=False)
        # Check if a new picture was uploaded
        if 'profile_picture' in self.request.FILES:
            # If there's an existing picture, consider deleting it to save storage
            if user.profile_picture:
                try:
                    old_pic = user.profile_picture.path
                    import os
                    if os.path.exists(old_pic):
                        os.remove(old_pic)
                except:
                    pass  # Ignore errors in cleanup
        user.save()
        messages.success(self.request, "Profile picture updated successfully!")
        return super().form_valid(form)
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.user_type != 'LANDLORD':
            messages.warning(request, "Access denied. Landlord privileges required.")
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)


@method_decorator(login_required, name='dispatch')
class VerificationDocumentsView(UpdateView):
    """View for updating landlord's verification documents."""
    model = LandlordProfile
    form_class = VerificationDocumentsForm
    template_name = 'accounts/verification_documents.html'
    success_url = reverse_lazy('landlord_profile')
    
    def get_object(self):
        return get_object_or_404(LandlordProfile, user=self.request.user)
    
    def form_valid(self, form):
        profile = form.save(commit=False)
        
        # If any document is uploaded, reset verification status to PENDING
        if ('id_document' in self.request.FILES or 
            'property_proof' in self.request.FILES or 
            'utility_bill' in self.request.FILES):
            
            if profile.verification_status == 'REJECTED':
                profile.verification_status = 'PENDING'
                profile.verification_notes = None
        
        profile.save()
        messages.success(self.request, "Verification documents uploaded successfully! Your documents will be reviewed.")
        return super().form_valid(form)
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.user_type != 'LANDLORD':
            messages.warning(request, "Access denied. Landlord privileges required.")
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)


# Admin verification views
class LandlordVerificationListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """View to list all landlords pending verification."""
    model = LandlordProfile
    template_name = 'accounts/landlord_verification_list.html'
    context_object_name = 'landlords'
    
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.user_type == 'ADMIN'
    
    def get_queryset(self):
        return LandlordProfile.objects.filter(verification_status='PENDING')

class LandlordVerificationDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """View to see details of a landlord pending verification."""
    model = LandlordProfile
    template_name = 'accounts/landlord_verification_detail.html'
    context_object_name = 'landlord'
    
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.user_type == 'ADMIN'



class LandlordVerificationDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """View to see details of a landlord pending verification."""
    model = LandlordProfile
    template_name = 'accounts/landlord_verification_detail.html'
    context_object_name = 'landlord'

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.user_type == 'ADMIN'
    
    def get_context_data(self, **kwargs):
        """Add extra context for debugging."""
        context = super().get_context_data(**kwargs)
        landlord = self.get_object()
        context['debug_pk'] = getattr(landlord, 'pk', None)
        return context


@login_required
def process_landlord_verification(request, pk):
    """Handle landlord verification approval or rejection."""
    if request.user.user_type != 'ADMIN':
        messages.warning(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    profile = get_object_or_404(LandlordProfile, pk=pk)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')
        
        if action == 'approve':
            profile.verification_status = 'APPROVED'
            profile.user.is_verified = True
            profile.user.save()
            profile.verified_at = timezone.now()
            profile.verification_notes = notes
            profile.save()
            
            # Send approval notification
            try:
                send_mail(
                    subject="Landlord Account Approved",
                    message=f"Congratulations! Your landlord account has been approved. You can now list your properties.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[profile.user.email],
                    fail_silently=True
                )
            except Exception as e:
                print(f"Error sending approval email: {str(e)}")
                
            messages.success(request, f"Landlord {profile.user.email} has been approved.")
            
        elif action == 'reject':
            profile.verification_status = 'REJECTED'
            profile.verification_notes = notes
            profile.save()
            
            # Send rejection notification
            try:
                send_mail(
                    subject="Landlord Account Verification Update",
                    message=f"Unfortunately, your landlord account verification was not approved. Reason: {notes}. Please address the issues and reapply.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[profile.user.email],
                    fail_silently=True
                )
            except Exception as e:
                print(f"Error sending rejection email: {str(e)}")
                
            messages.success(request, f"Landlord {profile.user.email} has been rejected.")
        
        return redirect('landlord_verification_list')
    
    return redirect('landlord_verification_detail', pk=pk)


@login_required
def reapply_verification(request, pk):
    """Allow rejected landlords to reapply with new documents."""
    profile = get_object_or_404(LandlordProfile, pk=pk, user=request.user)
    
    if profile.verification_status != 'REJECTED':
        messages.warning(request, "You can only reapply if your previous application was rejected.")
        return redirect('landlord_registration_success')
    
    if request.method == 'POST':
        form = LandlordProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            profile = form.save(commit=False)
            
            # Update verification documents if provided
            if 'id_document' in request.FILES:
                profile.id_document = request.FILES['id_document']
            if 'property_proof' in request.FILES:
                profile.property_proof = request.FILES['property_proof']
            if 'utility_bill' in request.FILES:
                profile.utility_bill = request.FILES['utility_bill']
                
            profile.verification_status = 'PENDING'
            profile.verification_notes = ''
            profile.save()
            
            # Notify admin about reapplication
            try:
                admin_emails = User.objects.filter(user_type='ADMIN').values_list('email', flat=True)
                if admin_emails:
                    send_mail(
                        subject="Landlord Reapplied for Verification",
                        message=f"Landlord ({request.user.email}) has reapplied for verification after rejection.",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=list(admin_emails),
                        fail_silently=True
                    )
            except Exception as e:
                print(f"Error sending reapplication notification: {str(e)}")
            
            messages.success(request, "Verification documents updated. Your application is now pending review.")
            return redirect('landlord_registration_success')
    else:
        form = LandlordProfileForm(instance=profile)
    
    return render(request, 'accounts/landlord_reapply.html', {'form': form, 'profile': profile})

def about_view(request):
    """
    View function for the About page
    """
    return render(request, 'accounts/about.html')

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

# Helper function to check if user is admin
def is_admin(user):
    return user.is_authenticated and user.user_type == 'ADMIN'

@login_required
@user_passes_test(is_admin)
def admin_landlord_list(request):
    """View to list all landlords for admin."""
    # Get all users with landlord type
    landlords = User.objects.filter(user_type='LANDLORD').select_related('landlord_profile')
    
    # Get verification status counts for the dashboard
    pending_count = LandlordProfile.objects.filter(verification_status='PENDING').count()
    approved_count = LandlordProfile.objects.filter(verification_status='APPROVED').count()
    rejected_count = LandlordProfile.objects.filter(verification_status='REJECTED').count()
    
    context = {
        'landlords': landlords,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
    }
    return render(request, 'accounts/landlord_list.html', context)

@login_required
@user_passes_test(is_admin)
def admin_add_landlord(request):
    """View to add a new landlord by admin."""
    if request.method == 'POST':
        user_form = LandlordForm(request.POST)
        profile_form = LandlordProfileForm(request.POST, request.FILES)
        
        if user_form.is_valid() and profile_form.is_valid():
            # Save user with landlord type
            user = user_form.save(commit=False)
            user.user_type = 'LANDLORD'
            user.is_verified = True
            user.set_password(user_form.cleaned_data['password'])
            user.save()
            
            # Save landlord profile
            profile = profile_form.save(commit=False)
            profile.user = user
            profile.verification_status = 'APPROVED'
            profile.verified_at = timezone.now()
            profile.save()
            
            messages.success(request, f'Landlord {user.email} has been created successfully.')
            return redirect('landlord_list')
    else:
        user_form = LandlordForm()
        profile_form = LandlordProfileForm()
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'title': 'Add New Landlord'
    }
    return render(request, 'accounts/landlord_form.html', context)

@login_required
@user_passes_test(is_admin)
def admin_edit_landlord(request, pk):
    """View to edit a landlord by admin."""
    landlord = get_object_or_404(User, pk=pk, user_type='LANDLORD')
    
    try:
        landlord_profile = landlord.landlord_profile
    except LandlordProfile.DoesNotExist:
        # Create a profile if it doesn't exist
        landlord_profile = LandlordProfile(user=landlord)
        landlord_profile.save()
    
    if request.method == 'POST':
        user_form = LandlordForm(request.POST, instance=landlord)
        profile_form = LandlordProfileForm(request.POST, request.FILES, instance=landlord_profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()
            profile = profile_form.save()
            
            # Update verification status if changed
            new_status = request.POST.get('verification_status')
            if new_status and new_status != landlord_profile.verification_status:
                landlord_profile.verification_status = new_status
                if new_status == 'APPROVED':
                    landlord_profile.verified_at = timezone.now()
                    landlord.is_verified = True
                    landlord.save()
                landlord_profile.save()
            
            messages.success(request, f'Landlord {user.email} has been updated successfully.')
            return redirect('landlord_list')
    else:
        user_form = LandlordForm(instance=landlord)
        profile_form = LandlordProfileForm(instance=landlord_profile)
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'landlord': landlord,
        'title': 'Edit Landlord'
    }
    return render(request, 'accounts/landlord_form.html', context)

@login_required
@user_passes_test(is_admin)
def admin_delete_landlord(request, pk):
    """View to delete a landlord."""
    landlord = get_object_or_404(User, pk=pk, user_type='LANDLORD')
    
    if request.method == 'POST':
        email = landlord.email
        landlord.delete()
        messages.success(request, f'Landlord {email} has been deleted successfully.')
        return redirect('landlord_list')
    
    context = {
        'landlord': landlord,
    }
    return render(request, 'accounts/landlord_confirm_delete.html', context)

@login_required
@user_passes_test(is_admin)
def verify_landlord(request, pk):
    """View to verify a landlord application."""
    landlord_profile = get_object_or_404(LandlordProfile, pk=pk)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        verification_notes = request.POST.get('verification_notes', '')
        
        if action == 'approve':
            landlord_profile.verification_status = 'APPROVED'
            landlord_profile.verified_at = timezone.now()
            landlord_profile.verification_notes = verification_notes
            landlord_profile.user.is_verified = True
            landlord_profile.user.save()
            messages.success(request, f'Landlord {landlord_profile.user.email} has been approved.')
        elif action == 'reject':
            landlord_profile.verification_status = 'REJECTED'
            landlord_profile.verification_notes = verification_notes
            messages.warning(request, f'Landlord {landlord_profile.user.email} has been rejected.')
        
        landlord_profile.save()
        
        # Send email notification to the landlord about their verification status
        try:
            status = "approved" if action == "approve" else "rejected"
            send_mail(
                subject=f"Your landlord application has been {status}",
                message=f"Your application to become a landlord has been {status}.\n\nNotes: {verification_notes}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[landlord_profile.user.email],
                fail_silently=True
            )
        except Exception as e:
            messages.error(request, f"Error sending email notification: {str(e)}")
        
        return redirect('landlord_verification_list')
    
    context = {
        'landlord': landlord_profile,
    }
    return render(request, 'accounts/verify_landlord.html', context)