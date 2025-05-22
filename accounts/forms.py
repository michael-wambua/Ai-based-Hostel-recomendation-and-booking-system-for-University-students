from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth import get_user_model

from hostels.models import Amenity
from .models import StudentProfile, LandlordProfile, User, StudentPreference

User = get_user_model()

class UserLoginForm(AuthenticationForm):
    """Form for user login."""
    
    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )

class StudentCreationForm(UserCreationForm):
    """Form for creating student users"""
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'phone_number']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

class UserRegistrationForm(UserCreationForm):
    """Base form for user registration."""
    
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    phone_number = forms.CharField(
        max_length=17,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number (optional)'})
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'})
    )
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'phone_number', 'password1', 'password2')
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with that email already exists.")
        return email


class StudentRegistrationForm(UserRegistrationForm):
    """Form for student registration."""
    
    university = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'University (optional)'})
    )
    course_of_study = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Course of Study (optional)'})
    )
    
    class Meta(UserRegistrationForm.Meta):
        fields = UserRegistrationForm.Meta.fields + ('university', 'course_of_study')
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 'STUDENT'
        if commit:
            user.save()
            StudentProfile.objects.create(
                user=user,
                university=self.cleaned_data.get('university', ''),
                course_of_study=self.cleaned_data.get('course_of_study', '')
            )
        return user


class LandlordRegistrationForm(UserRegistrationForm):
    """Form for landlord registration."""
    
    hostel_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'hostel_name'})
    )
    property_ownership_type = forms.ChoiceField(
        choices=LandlordProfile.PROPERTY_TYPE_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    id_document = forms.FileField(
        required=True,
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )
    property_proof = forms.FileField(
        required=True,
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )
    utility_bill = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )
    
    class Meta(UserRegistrationForm.Meta):
        fields = UserRegistrationForm.Meta.fields + (
            'hostel_name', 'property_ownership_type', 
            'id_document', 'property_proof', 'utility_bill'
        )
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 'LANDLORD'
        user.is_verified = False  # Landlords need verification
        if commit:
            user.save()
            LandlordProfile.objects.create(
                user=user,
                hostel_name=self.cleaned_data.get('hostel_name', ''),
                property_ownership_type=self.cleaned_data.get('property_ownership_type'),
                id_document=self.cleaned_data.get('id_document'),
                property_proof=self.cleaned_data.get('property_proof'),
                utility_bill=self.cleaned_data.get('utility_bill')
            )
        return user


class StudentProfileForm(forms.ModelForm):
    """Form for updating student profile."""
    
    class Meta:
        model = StudentProfile
        fields = ('student_id', 'phone', 'date_of_birth', 'address',
                 'university', 'course_of_study', 'budget_min', 'budget_max', 
                 'preferred_location', 'room_preference', 'preferred_amenities', 'gender', 'profile_picture')
        widgets = {
            'student_id': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'university': forms.TextInput(attrs={'class': 'form-control'}),
            'course_of_study': forms.TextInput(attrs={'class': 'form-control'}),
            'budget_min': forms.NumberInput(attrs={'class': 'form-control'}),
            'budget_max': forms.NumberInput(attrs={'class': 'form-control'}),
            'preferred_location': forms.TextInput(attrs={'class': 'form-control'}),
            'room_preference': forms.Select(attrs={'class': 'form-control'}),
            'preferred_amenities': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
        }


class LandlordProfileForm(forms.ModelForm):
    """Form for updating landlord profile."""
    
    class Meta:
        model = LandlordProfile
        fields = (
            'hostel_name', 
            'property_ownership_type', 
            'bio', 
            'years_of_experience',
            'preferred_contact_method',
            'available_hours',
            'facebook_link',
            'twitter_link',
            'instagram_link',
            'profile_picture'
        )
        widgets = {
            'hostel_name': forms.TextInput(attrs={'class': 'form-control'}),
            'property_ownership_type': forms.Select(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'years_of_experience': forms.NumberInput(attrs={'class': 'form-control'}),
            'preferred_contact_method': forms.Select(attrs={'class': 'form-control'}),
            'available_hours': forms.TextInput(attrs={'class': 'form-control'}),
            'facebook_link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://facebook.com/yourprofile'}),
            'twitter_link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://twitter.com/yourhandle'}),
            'instagram_link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://instagram.com/yourprofile'}),
        }
        
    def clean_facebook_link(self):
        url = self.cleaned_data.get('facebook_link')
        if url and not (url.startswith('http://') or url.startswith('https://')):
            return f'https://{url}'
        return url
        
    def clean_twitter_link(self):
        url = self.cleaned_data.get('twitter_link')
        if url and not (url.startswith('http://') or url.startswith('https://')):
            return f'https://{url}'
        return url
        
    def clean_instagram_link(self):
        url = self.cleaned_data.get('instagram_link')
        if url and not (url.startswith('http://') or url.startswith('https://')):
            return f'https://{url}'
        return url


class VerificationDocumentsForm(forms.ModelForm):
    """Form for uploading verification documents."""
    
    class Meta:
        model = LandlordProfile
        fields = ('id_document', 'property_proof', 'utility_bill')
        widgets = {
            'id_document': forms.FileInput(attrs={'class': 'form-control'}),
            'property_proof': forms.FileInput(attrs={'class': 'form-control'}),
            'utility_bill': forms.FileInput(attrs={'class': 'form-control'}),
        }
        help_texts = {
            'id_document': 'Upload a scanned copy of your government-issued ID (passport, driver\'s license, etc.)',
            'property_proof': 'Upload proof of property ownership or management rights',
            'utility_bill': 'Upload a recent utility bill with your name and address'
        }


class UserProfileForm(forms.ModelForm):
    """Form for updating user personal information."""
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'phone_number')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'readonly': True}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
        }


class ProfilePictureForm(forms.ModelForm):
    """Form for updating profile picture."""
    
    class Meta:
        model = LandlordProfile
        fields = ('profile_picture',)
        widgets = {
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'})
        }
class StudentPreferenceForm(forms.ModelForm):
    """Form for student housing preferences"""
    class Meta:
        model = StudentPreference
        fields = ['budget_min', 'budget_max', 'location', 'room_type', 'amenities']
        widgets = {
            'budget_min': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Minimum Budget'}),
            'budget_max': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Maximum Budget'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Preferred Location'}),
            'room_type': forms.Select(attrs={'class': 'form-select'}),
            'amenities': forms.CheckboxSelectMultiple(),
        }
    
class LandlordForm(forms.ModelForm):
    """Form for creating/editing landlord user"""
    password = forms.CharField(widget=forms.PasswordInput(), required=False, 
                             help_text="Leave empty to keep current password")
    
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'phone_number', 'is_verified']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make password not required for updates
        if self.instance.pk:
            self.fields['password'].required = False
        else:
            self.fields['password'].required = True

class LandlordProfileForm(forms.ModelForm):
    """Form for creating/editing landlord profile"""
    class Meta:
        model = LandlordProfile
        fields = [
            'hostel_name', 'property_ownership_type', 'bio', 
            'years_of_experience', 'preferred_contact_method',
            'available_hours', 'id_document', 'property_proof', 
            'utility_bill', 'profile_picture', 'verification_status',
            'verification_notes', 'facebook_link', 'twitter_link', 
            'instagram_link'
        ]
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
            'verification_notes': forms.Textarea(attrs={'rows': 3}),
        }