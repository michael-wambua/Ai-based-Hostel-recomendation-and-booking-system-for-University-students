from django import forms
from django.forms import inlineformset_factory
from .models import Hostel, Room, HostelImage, RoomImage, Amenity, RoomType, Review, ReviewImage, ReviewReply

class AmenityForm(forms.ModelForm):
    class Meta:
        model = Amenity
        fields = ['name', 'icon']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'icon': forms.TextInput(attrs={'class': 'form-control'}),
        }

class RoomTypeForm(forms.ModelForm):
    class Meta:
        model = RoomType
        fields = ['name', 'capacity', 'base_price', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'base_price': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class HostelForm(forms.ModelForm):
    amenities = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter amenities separated by commas'})
    )

    class Meta:
        model = Hostel
        fields = [
            'name', 'description', 'address', 'city', 'state', 'zip_code',
             'university_name', 'latitude', 'longitude', 'distance_from_university',
            'rules', 'amenities'
        ]
        #  'distance_from_university',
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'zip_code': forms.TextInput(attrs={'class': 'form-control'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control'}),
            'distance_from_university': forms.NumberInput(attrs={'class': 'form-control'}),
            'university_name': forms.TextInput(attrs={'class': 'form-control'}),
            'rules': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

    def save(self, commit=True):
        hostel = super().save(commit=False)

        if commit:
            hostel.save()

            # Process amenities manually entered by the landlord
            amenities_list = self.cleaned_data['amenities'].split(',')
            for amenity in amenities_list:
                amenity_name = amenity.strip()
                if amenity_name:  # Avoid empty values
                    amenity_obj, created = Amenity.objects.get_or_create(name=amenity_name)
                    hostel.amenities.add(amenity_obj)

        return hostel

class HostelImageForm(forms.ModelForm):
    class Meta:
        model = HostelImage
        fields = ['image', 'is_main', 'caption']
        widgets = {
            'caption': forms.TextInput(attrs={'class': 'form-control'}),
            'is_main': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

# Create formset for multiple hostel images
HostelImageFormSet = inlineformset_factory(
    Hostel, HostelImage, 
    form=HostelImageForm, 
    extra=3, 
    can_delete=True
)

class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = [
            'room_type', 'room_number', 'description', 'price_per_month', 
            'security_deposit', 'capacity', 'size', 'availability_status',
            'gender_restriction'
        ]
        widgets = {
            'room_type': forms.Select(attrs={'class': 'form-control'}),
            'room_number': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'price_per_month': forms.NumberInput(attrs={'class': 'form-control'}),
            'security_deposit': forms.NumberInput(attrs={'class': 'form-control'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control'}),
            'size': forms.NumberInput(attrs={'class': 'form-control'}),
            'availability_status': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'gender_restriction': forms.Select(attrs={'class': 'form-control'}),
        }

class RoomImageForm(forms.ModelForm):
    class Meta:
        model = RoomImage
        fields = ['image', 'is_main', 'caption']
        widgets = {
            'caption': forms.TextInput(attrs={'class': 'form-control'}),
            'is_main': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

# Create formset for multiple room images
RoomImageFormSet = inlineformset_factory(
    Room, RoomImage, 
    form=RoomImageForm, 
    extra=3, 
    can_delete=True
)

class HostelSearchForm(forms.Form):
    """Form for searching and filtering hostels"""
    search_query = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search for hostels...'})
    )
    university = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'University name'})
    )
    city = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'})
    )
    min_price = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Min price'})
    )
    max_price = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Max price'})
    )
    room_type = forms.ModelChoiceField(
        queryset=RoomType.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    amenities = forms.ModelMultipleChoiceField(
        queryset=Amenity.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple()
    )
    gender_restriction = forms.ChoiceField(
        choices=[('', 'Any'), ('male', 'Male Only'), ('female', 'Female Only'), ('any', 'No Restriction')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    max_distance = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Max distance (km)'})
    )

class ReviewForm(forms.ModelForm):
    """Form for submitting a review for a hostel"""
    
    class Meta:
        model = Review
        fields = [
            'rating', 
            'cleanliness_rating', 
            'location_rating', 
            'value_rating', 
            'facility_rating', 
            'comment'
        ]
        widgets = {
            'rating': forms.RadioSelect(
                choices=[(i, f"{i} Stars") for i in range(1, 6)],
                attrs={'class': 'rating-input'}
            ),
            'cleanliness_rating': forms.RadioSelect(
                choices=[(i, f"{i}") for i in range(1, 6)],
                attrs={'class': 'category-rating-input'}
            ),
            'location_rating': forms.RadioSelect(
                choices=[(i, f"{i}") for i in range(1, 6)],
                attrs={'class': 'category-rating-input'}
            ),
            'value_rating': forms.RadioSelect(
                choices=[(i, f"{i}") for i in range(1, 6)],
                attrs={'class': 'category-rating-input'}
            ),
            'facility_rating': forms.RadioSelect(
                choices=[(i, f"{i}") for i in range(1, 6)],
                attrs={'class': 'category-rating-input'}
            ),
            'comment': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Share your experience...'})
        }
        labels = {
            'rating': 'Overall Rating',
            'cleanliness_rating': 'Cleanliness',
            'location_rating': 'Location',
            'value_rating': 'Value for Money',
            'facility_rating': 'Facilities',
            'comment': 'Your Review'
        }

class ReviewImageForm(forms.ModelForm):
    """Form for uploading images with a review"""
    
    class Meta:
        model = ReviewImage
        fields = ['image', 'caption']
        widgets = {
            'caption': forms.TextInput(attrs={'placeholder': 'Briefly describe this image'})
        }

class ReviewReplyForm(forms.ModelForm):
    class Meta:
        model = ReviewReply
        fields = ['comment']
        widgets = {
            'comment': forms.Textarea(
                attrs={
                    'rows': 3,
                    'placeholder': 'Respond to this review...',
                    'class': 'form-control'
                }
            )
        }
        labels = {
            'comment': 'Your Response'
        }

# For use in the view to handle multiple image uploads
ReviewImageFormSet = forms.inlineformset_factory(
    Review, 
    ReviewImage,
    form=ReviewImageForm,
    extra=3,  # Allow uploading up to 3 images
    max_num=5,  # Maximum 5 images total
    can_delete=True
)