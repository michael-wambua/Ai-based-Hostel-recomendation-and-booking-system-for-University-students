from django.urls import path
from . import views


urlpatterns = [
    # Public views
    path('', views.hostel_list, name='hostel_list'),
    path('<int:hostel_id>/', views.hostel_detail, name='hostel_detail'),
    path('<int:hostel_id>/room/<int:room_id>/', views.room_detail, name='room_detail'),
    path('compare/', views.compare_hostels, name='compare_hostels'),
    #path('hostel/detail/<int:hostel_id>/', views.hostel_detail, name='hostel_detail'),
    
    # Landlord views
    path('my-hostels/', views.landlord_hostels, name='landlord_hostels'),
    path('landlord/tenants/', views.landlord_tenants, name='landlord_tenants'),
    path('add/', views.add_hostel, name='add_hostel'),
    path('<int:hostel_id>/edit/', views.edit_hostel, name='edit_hostel'),
    path('<int:hostel_id>/delete/', views.delete_hostel, name='delete_hostel'),
    path('<int:hostel_id>/rooms/', views.room_list, name='room_list'),
    path('<int:hostel_id>/add-room/', views.add_room, name='add_room'),
    path('<int:hostel_id>/room/<int:room_id>/edit/', views.edit_room, name='edit_room'),
    path('<int:hostel_id>/room/<int:room_id>/delete/', views.delete_room, name='delete_room'),
    path('room/<int:room_id>/toggle-availability/', views.toggle_room_availability, name='toggle_room_availability'),
    

    path('landlord/amenities/', views.amenity_list, name='amenity_list'),
    path('landlord/amenities/add/', views.add_amenity, name='add_amenity'),
    path('landlord/room-types/', views.room_type_list, name='room_type_list'),
    path('landlord/room-types/add/', views.add_room_type, name='add_room_type'),
    path('<int:hostel_id>/room-types/<int:room_type_id>/edit/', views.edit_room_type, name='edit_room_type'),
    
    # User views
    path('shortlist/', views.user_shortlist, name='user_shortlist'),
    path('toggle-shortlist/', views.toggle_shortlist, name='toggle_shortlist'),
    path('get-shortlisted-count/', views.get_shortlisted_count, name='get_shortlisted_count'),
    path('remove_shortlist/', views.remove_shortlist, name='remove_shortlist'),

    # Reviews
    path('hostel/<int:hostel_id>/reviews/', views.hostel_reviews, name='hostel_reviews'),
    path('hostel/<int:hostel_id>/add-review/', views.add_review, name='add_review'),
    path('review/<int:review_id>/edit/', views.edit_review, name='edit_review'),
    path('review/<int:review_id>/delete/', views.delete_review, name='delete_review'),
    path('review/<int:review_id>/reply/', views.add_review_reply, name='add_review_reply'),
]