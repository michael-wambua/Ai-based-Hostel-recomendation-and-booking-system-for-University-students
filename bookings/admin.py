from django.contrib import admin
from .models import Booking

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('student', 'get_hostel', 'get_room', 'start_date', 'end_date', 'status')
    list_filter = ('status', 'start_date', 'end_date')
    search_fields = ('student__username', 'student__email', 'room__hostel__name', 'room__room_number')
    date_hierarchy = 'booking_date'
    
    def get_hostel(self, obj):
        return obj.room.hostel.name
    get_hostel.short_description = 'Hostel'
    
    def get_room(self, obj):
        return obj.room.room_number
    get_room.short_description = 'Room'