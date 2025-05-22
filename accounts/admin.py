# admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, StudentProfile, LandlordProfile

class StudentProfileInline(admin.StackedInline):
    model = StudentProfile
    can_delete = False
    verbose_name_plural = 'student profile'

class LandlordProfileInline(admin.StackedInline):
    model = LandlordProfile
    can_delete = False
    verbose_name_plural = 'landlord profile'

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Define admin model for custom User model with no username field."""
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'phone_number')}),
        (_('User type'), {'fields': ('user_type', 'is_verified')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'user_type'),
        }),
    )
    list_display = ('email', 'first_name', 'last_name', 'user_type', 'is_verified', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    list_filter = ('user_type', 'is_verified', 'is_staff', 'is_superuser', 'is_active')
    
    def get_inlines(self, request, obj=None):
        if obj:
            if obj.user_type == 'STUDENT':
                return [StudentProfileInline]
            elif obj.user_type == 'LANDLORD':
                return [LandlordProfileInline]
        return []
    
    def delete_model(self, request, obj):
        # Delete related profiles when deleting a User
        if obj.user_type == 'STUDENT':
            StudentProfile.objects.filter(user=obj).delete()
        elif obj.user_type == 'LANDLORD':
            LandlordProfile.objects.filter(user=obj).delete()
        # Call the parent method to actually delete the user
        super().delete_model(request, obj)


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'university', 'course_of_study', 'budget_min', 'budget_max')
    search_fields = ('user__email', 'university', 'course_of_study')
    list_filter = ('room_preference', 'gender')


@admin.register(LandlordProfile)
class LandlordProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'hostel_name', 'property_ownership_type', 'verification_status')
    search_fields = ('user__email', 'hostel_name', 'property_ownership_type')
    list_filter = ('property_ownership_type', 'verification_status')
    readonly_fields = ('verified_at',)

    def save_model(self, request, obj, form, change):
        """Ensure is_verified updates when admin approves a landlord."""
        if obj.verification_status == "APPROVED":
            obj.user.is_verified = True
            obj.user.save()
        elif obj.verification_status == "REJECTED":
            obj.user.is_verified = False
            obj.user.save()
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        """Delete related user when deleting landlord profile."""
        if obj.user:
            obj.user.delete()
        super().delete_model(request, obj)


