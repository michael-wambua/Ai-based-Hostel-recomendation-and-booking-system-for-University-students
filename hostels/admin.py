from django.contrib import admin
from .models import (
    Hostel, Room, Amenity, RoomType, 
    HostelImage, RoomImage, Availability
)

class HostelImageInline(admin.TabularInline):
    model = HostelImage
    extra = 3

class RoomInline(admin.TabularInline):
    model = Room
    extra = 1
    show_change_link = True

@admin.register(Hostel)
class HostelAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'city', 'created_at')
    list_filter = ('city', 'created_at')
    search_fields = ('name', 'description', 'address', 'city')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [HostelImageInline, RoomInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'owner', 'description')
        }),
        ('Location', {
            'fields': ('address', 'city', 'state', 'zip_code', 'latitude', 'longitude')
        }),
        ('University', {
            'fields': ('university_name', 'distance_from_university')
        }),
        ('Additional Info', {
            'fields': ('rules', 'amenities', 'verification_status')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(owner=request.user)

class RoomImageInline(admin.TabularInline):
    model = RoomImage
    extra = 3

class AvailabilityInline(admin.TabularInline):
    model = Availability
    extra = 1

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('room_number', 'hostel', 'room_type', 'price_per_month', 'capacity', 'availability_status')
    list_filter = ('room_type', 'availability_status', 'gender_restriction')
    search_fields = ('room_number', 'description', 'hostel__name')
    inlines = [RoomImageInline, AvailabilityInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('hostel', 'room_number', 'room_type', 'description')
        }),
        ('Pricing', {
            'fields': ('price_per_month', 'security_deposit')
        }),
        ('Details', {
            'fields': ('capacity', 'size', 'availability_status', 'gender_restriction')
        }),
        ('Amenities', {
            'fields': ('amenities',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(hostel__owner=request.user)

@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon')
    search_fields = ('name',)

@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name', 'description')

@admin.register(HostelImage)
class HostelImageAdmin(admin.ModelAdmin):
    list_display = ('hostel', 'caption', 'is_main', 'created_at')
    list_filter = ('is_main', 'created_at')
    search_fields = ('hostel__name', 'caption')

@admin.register(RoomImage)
class RoomImageAdmin(admin.ModelAdmin):
    list_display = ('room', 'caption', 'is_main', 'created_at')
    list_filter = ('is_main', 'created_at')
    search_fields = ('room__name', 'caption')

@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    list_display = ('room', 'start_date', 'end_date', 'is_available')
    list_filter = ('is_available', 'start_date')
    search_fields = ('room__name', 'room__hostel__name')