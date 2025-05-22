from django import forms
from .models import Booking
from hostels.models import Room
import datetime
from datetime import timedelta

class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['room', 'start_date', 'end_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.student = kwargs.pop('student', None)
        self.hostel_id = kwargs.pop('hostel_id', None)
        super(BookingForm, self).__init__(*args, **kwargs)
        
        if self.hostel_id:
            # Using True instead of 'Available' since availability_status is a BooleanField
            self.fields['room'].queryset = Room.objects.filter(
                hostel_id=self.hostel_id,
                availability_status=True  # It's a boolean field, so use True instead of 'Available'
            )
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        room = cleaned_data.get('room')
        
        if start_date and end_date:
            if start_date < datetime.date.today():
                raise forms.ValidationError("Start date cannot be in the past.")
            
            if end_date <= start_date:
                raise forms.ValidationError("End date must be after start date.")
            
            # Check if room is available for the selected dates
            conflicting_bookings = Booking.objects.filter(
                room=room,
                status='CONFIRMED',
            ).exclude(
                end_date__lte=start_date
            ).exclude(
                start_date__gte=end_date
            )
            
            if conflicting_bookings.exists():
                raise forms.ValidationError("This room is not available for the selected dates.")
                
        return cleaned_data

class BookingCancellationForm(forms.Form):
    cancellation_reason = forms.CharField(
        widget=forms.Textarea,
        required=True,
        label="Reason for cancellation"
    )

class ExtendStayForm(forms.Form):
    new_end_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    
    def __init__(self, booking, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.booking = booking
        # Set minimum date to one day after current end date
        self.fields['new_end_date'].widget.attrs['min'] = (self.booking.end_date + timedelta(days=1)).strftime('%Y-%m-%d')
        
    def clean_new_end_date(self):
        new_end_date = self.cleaned_data['new_end_date']
        
        # Ensure new end date is after current end date
        if new_end_date <= self.booking.end_date:
            raise forms.ValidationError("New check-out date must be after current check-out date")
            
        # Check room availability for the extended period
        overlapping_bookings = Booking.objects.filter(
            room=self.booking.room,
            start_date__lt=new_end_date,
            end_date__gt=self.booking.end_date
        ).exclude(id=self.booking.id)
        
        if overlapping_bookings.exists():
            raise forms.ValidationError("Room is not available for the requested extension period")
            
        return new_end_date