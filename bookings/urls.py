from django.urls import path
from . import views

app_name = 'bookings'

urlpatterns = [
    # Student URLs
    path('student/dashboard/', views.student_bookings_dashboard, name='student_dashboard'),
    path('book-hostel/<int:hostel_id>/', views.book_hostel, name='book_hostel'),
    path('hostel-list/', views.hostel_list, name='hostel_list'),
    path('cancel-booking/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
    path('extend_stay/<int:booking_id>/', views.extend_stay, name='extend_stay'),
    path('student/booking/<int:booking_id>/', views.booking_detail, name='booking_detail'),
    
    # Landlord URLs
    path('landlord/dashboard/', views.landlord_dashboard, name='landlord_dashboard'),
    path('landlord/requests/', views.booking_requests, name='booking_requests'),
    path('booking/<int:booking_id>/approve/', views.approve_booking, name='approve_booking'),
    path('booking/<int:booking_id>/reject/', views.reject_booking, name='reject_booking'),

    # Admin URLs
    path('admin/bookings/', views.admin_bookings, name='admin_bookings'),
    path('admin/terminate-booking/<int:booking_id>/', views.terminate_booking, name='terminate_booking'),
]
