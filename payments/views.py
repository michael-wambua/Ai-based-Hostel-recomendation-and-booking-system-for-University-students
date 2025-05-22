from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.urls import reverse
from django.core.paginator import Paginator
from django.http import HttpResponseForbidden
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
import io
import xlsxwriter
from .models import Invoice, Payment, PaymentStatus
from .forms import PaymentForm, PaymentConfirmationForm, InvoiceForm
from bookings.models import Booking, BookingStatus
from hostels.models import Hostel, Room
from accounts.models import LandlordProfile

# Student Views
@login_required
def student_payments(request):
    """View for students to see all their invoices/payments"""
    # Get all bookings for this student
    bookings = Booking.objects.filter(student=request.user)
    
    # Get all invoices related to these bookings
    invoices = Invoice.objects.filter(booking__in=bookings).order_by('-created_at')
    
    # Categorize invoices
    pending_invoices = invoices.filter(status=PaymentStatus.PENDING)
    paid_invoices = invoices.filter(status=PaymentStatus.PAID)
    confirmed_invoices = invoices.filter(status=PaymentStatus.CONFIRMED)
    expired_invoices = invoices.filter(status=PaymentStatus.EXPIRED)
    
    # Check for overdue invoices and mark them as expired
    for invoice in pending_invoices:
        if invoice.is_overdue:
            invoice.status = PaymentStatus.EXPIRED
            invoice.save()
    
    return render(request, 'payments/student/payments_list.html', {
        'pending_invoices': pending_invoices,
        'paid_invoices': paid_invoices,
        'confirmed_invoices': confirmed_invoices,
        'expired_invoices': expired_invoices,
    })

@login_required
def invoice_detail(request, invoice_id):
    """View for students to see invoice details and submit payment"""
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    # Ensure this invoice belongs to the logged-in student
    if invoice.booking.student != request.user:
        return HttpResponseForbidden("You don't have permission to view this invoice")
    
    # Check if payment already exists
    try:
        payment = invoice.payment
        payment_exists = True
    except Payment.DoesNotExist:
        payment = None
        payment_exists = False
    
    if request.method == 'POST' and not payment_exists and invoice.status == PaymentStatus.PENDING:
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.invoice = invoice
            payment.save()
            
            # Update invoice status
            invoice.status = PaymentStatus.PAID
            invoice.save()
            
            messages.success(request, "Payment information submitted successfully. Awaiting landlord confirmation.")
            return redirect('payments:student_payments')
    else:
        form = PaymentForm()
    
    return render(request, 'payments/student/invoice_detail.html', {
        'invoice': invoice,
        'payment': payment,
        'form': form,
        'payment_exists': payment_exists,
    })

# Landlord Views
@login_required
def landlord_payments(request):
    """View for landlords to see all payments for their properties"""
    try:
        landlord_profile = LandlordProfile.objects.get(user=request.user)
    except LandlordProfile.DoesNotExist:
        messages.error(request, "You don't have access to this page. Only landlords can view payments.")
        return redirect('home')
    
    # Get all hostels owned by the landlord
    hostels = Hostel.objects.filter(owner=landlord_profile)
    
    # Get all rooms in these hostels
    rooms = Room.objects.filter(hostel__in=hostels)
    
    # Get all bookings for these rooms
    bookings = Booking.objects.filter(room__in=rooms)
    
    # Get all invoices for these bookings
    invoices = Invoice.objects.filter(booking__in=bookings).order_by('-created_at')
    
    # Categorize invoices
    pending_invoices = invoices.filter(status=PaymentStatus.PENDING)
    paid_invoices = invoices.filter(status=PaymentStatus.PAID)
    confirmed_invoices = invoices.filter(status=PaymentStatus.CONFIRMED)
    expired_invoices = invoices.filter(Q(status=PaymentStatus.EXPIRED) | Q(status=PaymentStatus.CANCELLED))
    
    # Check for payments awaiting confirmation
    payments_to_confirm = Payment.objects.filter(invoice__in=paid_invoices)
    confirm_count = payments_to_confirm.count()
    
    return render(request, 'payments/landlord/payments_list.html', {
        'pending_invoices': pending_invoices,
        'paid_invoices': paid_invoices,
        'confirmed_invoices': confirmed_invoices,
        'expired_invoices': expired_invoices,
        'payments_to_confirm': payments_to_confirm,
        'confirm_count': confirm_count,
    })

@login_required
def confirm_payment(request, payment_id):
    """View for landlords to confirm a payment"""
    payment = get_object_or_404(Payment, id=payment_id)
    invoice = payment.invoice
    booking = invoice.booking
    
    # Check if the logged-in user is the landlord of this property
    try:
        landlord_profile = LandlordProfile.objects.get(user=request.user)
        if booking.room.hostel.owner != landlord_profile:
            messages.error(request, "You don't have permission to confirm this payment")
            return redirect('payments:landlord_payments')
    except LandlordProfile.DoesNotExist:
        messages.error(request, "You don't have permission to confirm payments")
        return redirect('home')
    
    if request.method == 'POST':
        form = PaymentConfirmationForm(request.POST)
        if form.is_valid():
            # Confirm the payment
            payment.confirm_payment(request.user)
            
            # Update notes if provided
            if form.cleaned_data['notes']:
                payment.notes = form.cleaned_data['notes']
                payment.save()
            
            messages.success(request, f"Payment for Booking #{booking.id} has been confirmed")
            return redirect('payments:landlord_payments')
    else:
        form = PaymentConfirmationForm()
    
    return render(request, 'payments/landlord/confirm_payment.html', {
        'payment': payment,
        'invoice': invoice,
        'booking': booking,
        'form': form,
    })

@login_required
def create_invoice(request, booking_id):
    """View for landlords to manually create an invoice"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Check if logged-in user is the landlord of this property
    try:
        landlord_profile = LandlordProfile.objects.get(user=request.user)
        if booking.room.hostel.owner != landlord_profile:
            messages.error(request, "You don't have permission to create an invoice for this booking")
            return redirect('payments:landlord_payments')
    except LandlordProfile.DoesNotExist:
        messages.error(request, "You don't have permission to create invoices")
        return redirect('home')
    
    # Check if invoice already exists
    try:
        invoice = Invoice.objects.get(booking=booking)
        messages.warning(request, "An invoice already exists for this booking")
        return redirect('payments:landlord_payments')
    except Invoice.DoesNotExist:
        pass
    
    if request.method == 'POST':
        form = InvoiceForm(request.POST)
        if form.is_valid():
            invoice = form.save(commit=False)
            invoice.booking = booking
            invoice.save()
            
            messages.success(request, f"Invoice created successfully for Booking #{booking.id}")
            return redirect('payments:landlord_payments')
    else:
        # Pre-fill with suggested values
        initial_amount = booking.room.price if hasattr(booking.room, 'price') else 0
        form = InvoiceForm(initial={
            'amount': initial_amount,
            'due_date': timezone.now() + timezone.timedelta(days=3)
        })
    
    return render(request, 'payments/landlord/create_invoice.html', {
        'form': form,
        'booking': booking,
    })

# Admin Views
@login_required
def admin_payments(request):
    """View for admins to see all payments"""
    if not request.user.is_staff:
        messages.error(request, "You are not authorized to view this page.")
        return redirect('home')
    
    invoices = Invoice.objects.all().order_by('-created_at')
    paginator = Paginator(invoices, 20)  # Show 20 invoices per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'payments/admin/payments_list.html', {
        'page_obj': page_obj,
    })

@login_required
def export_payments_pdf(request):
    """Export payments data as PDF for landlords"""
    try:
        landlord_profile = LandlordProfile.objects.get(user=request.user)
    except LandlordProfile.DoesNotExist:
        messages.error(request, "You don't have access to this feature. Only landlords can export payments.")
        return redirect('home')
    
    # Get all hostels owned by the landlord
    hostels = Hostel.objects.filter(owner=landlord_profile)
    rooms = Room.objects.filter(hostel__in=hostels)
    bookings = Booking.objects.filter(room__in=rooms)
    invoices = Invoice.objects.filter(booking__in=bookings).order_by('-created_at')
    
    # Categorize invoices
    pending_invoices = invoices.filter(status=PaymentStatus.PENDING)
    paid_invoices = invoices.filter(status=PaymentStatus.PAID)
    confirmed_invoices = invoices.filter(status=PaymentStatus.CONFIRMED)
    expired_invoices = invoices.filter(Q(status=PaymentStatus.EXPIRED) | Q(status=PaymentStatus.CANCELLED))
    
    # Get payments awaiting confirmation
    payments_to_confirm = Payment.objects.filter(invoice__in=paid_invoices)
    
    # Prepare template context
    context = {
        'landlord': landlord_profile,
        'pending_invoices': pending_invoices,
        'paid_invoices': paid_invoices,
        'confirmed_invoices': confirmed_invoices,
        'expired_invoices': expired_invoices,
        'payments_to_confirm': payments_to_confirm,
        'date_generated': timezone.now()
    }
    
    # Get template
    template = get_template('payments/landlord/payments_pdf.html')
    html = template.render(context)
    
    # Create PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="payments_report_{timezone.now().strftime("%Y%m%d")}.pdf"'
    
    # Generate PDF
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('PDF generation error', status=500)
    
    return response

@login_required
def export_payments_excel(request):
    """Export payments data as Excel for landlords"""
    try:
        landlord_profile = LandlordProfile.objects.get(user=request.user)
    except LandlordProfile.DoesNotExist:
        messages.error(request, "You don't have access to this feature. Only landlords can export payments.")
        return redirect('home')
    
    # Get all hostels owned by the landlord
    hostels = Hostel.objects.filter(owner=landlord_profile)
    rooms = Room.objects.filter(hostel__in=hostels)
    bookings = Booking.objects.filter(room__in=rooms)
    invoices = Invoice.objects.filter(booking__in=bookings).order_by('-created_at')
    
    # Create Excel file
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output)
    
    # Add header format
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#4a90e2',
        'font_color': 'white',
        'border': 1
    })
    
    # Add cell format
    cell_format = workbook.add_format({
        'border': 1
    })
    
    # Create worksheets for different payment categories
    pending_sheet = workbook.add_worksheet('Pending Invoices')
    confirm_sheet = workbook.add_worksheet('Awaiting Confirmation')
    confirmed_sheet = workbook.add_worksheet('Confirmed Payments')
    expired_sheet = workbook.add_worksheet('Expired Invoices')
    
    # Define headers
    pending_headers = ['ID', 'Student', 'Hostel/Room', 'Amount', 'Created', 'Due Date', 'Days Left']
    confirm_headers = ['ID', 'Student', 'Hostel/Room', 'Amount', 'Payment Date', 'Transaction Code']
    confirmed_headers = ['ID', 'Student', 'Hostel/Room', 'Amount', 'Payment Date', 'Confirmed Date', 'Transaction Code']
    expired_headers = ['ID', 'Student', 'Hostel/Room', 'Amount', 'Created', 'Due Date', 'Status']
    
    # Write headers to each sheet
    for col, header in enumerate(pending_headers):
        pending_sheet.write(0, col, header, header_format)
        
    for col, header in enumerate(confirm_headers):
        confirm_sheet.write(0, col, header, header_format)
        
    for col, header in enumerate(confirmed_headers):
        confirmed_sheet.write(0, col, header, header_format)
        
    for col, header in enumerate(expired_headers):
        expired_sheet.write(0, col, header, header_format)
    
    # Write data to pending invoices sheet
    pending_invoices = invoices.filter(status=PaymentStatus.PENDING)
    for row, invoice in enumerate(pending_invoices, start=1):
        days_remaining = invoice.days_remaining
        days_text = f"{days_remaining} days" if days_remaining > 0 else "Overdue"
        
        # Get room identifier - using str(room) as a fallback if name doesn't exist
        room = invoice.booking.room
        room_id = getattr(room, 'number', getattr(room, 'room_number', str(room)))
        hostel_name = invoice.booking.room.hostel.name
        
        pending_sheet.write(row, 0, invoice.id, cell_format)
        pending_sheet.write(row, 1, invoice.booking.student.get_full_name() or invoice.booking.student.username, cell_format)
        pending_sheet.write(row, 2, f"{hostel_name} / {room_id}", cell_format)
        pending_sheet.write(row, 3, f"${invoice.amount}", cell_format)
        pending_sheet.write(row, 4, invoice.created_at.strftime("%b %d, %Y"), cell_format)
        pending_sheet.write(row, 5, invoice.due_date.strftime("%b %d, %Y"), cell_format)
        pending_sheet.write(row, 6, days_text, cell_format)
    
    # Write data to payments awaiting confirmation sheet
    payments_to_confirm = Payment.objects.filter(invoice__in=invoices.filter(status=PaymentStatus.PAID))
    for row, payment in enumerate(payments_to_confirm, start=1):
        # Get room identifier
        room = payment.invoice.booking.room
        room_id = getattr(room, 'number', getattr(room, 'room_number', str(room)))
        hostel_name = payment.invoice.booking.room.hostel.name
        
        confirm_sheet.write(row, 0, payment.invoice.id, cell_format)
        confirm_sheet.write(row, 1, payment.invoice.booking.student.get_full_name() or payment.invoice.booking.student.username, cell_format)
        confirm_sheet.write(row, 2, f"{hostel_name} / {room_id}", cell_format)
        confirm_sheet.write(row, 3, f"${payment.invoice.amount}", cell_format)
        confirm_sheet.write(row, 4, payment.payment_date.strftime("%b %d, %Y %H:%M"), cell_format)
        confirm_sheet.write(row, 5, payment.transaction_code, cell_format)
    
    # Write data to confirmed payments sheet
    confirmed_invoices = invoices.filter(status=PaymentStatus.CONFIRMED)
    for row, invoice in enumerate(confirmed_invoices, start=1):
        try:
            payment = invoice.payment
            
            # Get room identifier
            room = invoice.booking.room
            room_id = getattr(room, 'number', getattr(room, 'room_number', str(room)))
            hostel_name = invoice.booking.room.hostel.name
            
            confirmed_sheet.write(row, 0, invoice.id, cell_format)
            confirmed_sheet.write(row, 1, invoice.booking.student.get_full_name() or invoice.booking.student.username, cell_format)
            confirmed_sheet.write(row, 2, f"{hostel_name} / {room_id}", cell_format)
            confirmed_sheet.write(row, 3, f"${invoice.amount}", cell_format)
            confirmed_sheet.write(row, 4, payment.payment_date.strftime("%b %d, %Y"), cell_format)
            confirmed_sheet.write(row, 5, payment.confirmed_date.strftime("%b %d, %Y") if payment.confirmed_date else "N/A", cell_format)
            confirmed_sheet.write(row, 6, payment.transaction_code, cell_format)
        except Payment.DoesNotExist:
            pass
    
    # Write data to expired invoices sheet
    expired_invoices = invoices.filter(Q(status=PaymentStatus.EXPIRED) | Q(status=PaymentStatus.CANCELLED))
    for row, invoice in enumerate(expired_invoices, start=1):
        # Get room identifier
        room = invoice.booking.room
        room_id = getattr(room, 'number', getattr(room, 'room_number', str(room)))
        hostel_name = invoice.booking.room.hostel.name
        
        expired_sheet.write(row, 0, invoice.id, cell_format)
        expired_sheet.write(row, 1, invoice.booking.student.get_full_name() or invoice.booking.student.username, cell_format)
        expired_sheet.write(row, 2, f"{hostel_name} / {room_id}", cell_format)
        expired_sheet.write(row, 3, f"${invoice.amount}", cell_format)
        expired_sheet.write(row, 4, invoice.created_at.strftime("%b %d, %Y"), cell_format)
        expired_sheet.write(row, 5, invoice.due_date.strftime("%b %d, %Y"), cell_format)
        expired_sheet.write(row, 6, dict(PaymentStatus.CHOICES)[invoice.status], cell_format)
    
    # Set column widths for better readability
    for sheet in [pending_sheet, confirm_sheet, confirmed_sheet, expired_sheet]:
        sheet.set_column(0, 0, 8)  # ID column
        sheet.set_column(1, 1, 25)  # Student column
        sheet.set_column(2, 2, 30)  # Hostel/Room column
        sheet.set_column(3, 6, 15)  # Other columns
    
    workbook.close()
    
    # Create response
    output.seek(0)
    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="payments_report_{timezone.now().strftime("%Y%m%d")}.xlsx"'
    
    return response