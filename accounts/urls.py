from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('about/', views.about_view, name='about'),
    
    # Registration
    path('register/student/', views.register_student, name='register_student'),
    path('register/landlord/', views.register_landlord, name='register_landlord'),
    
    # Dashboard routes
    path('dashboard/', views.dashboard, name='dashboard'),  # Main router
    path('dashboard/student/', views.student_dashboard, name='student_dashboard'),
    path('dashboard/landlord/', views.landlord_dashboard, name='landlord_dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    
    # Student profile
    path('student/profile/setup/', views.student_profile_setup, name='student_profile_setup'),
    path('student/profile/', views.StudentProfileView.as_view(), name='student_profile'),
    path('student/profile/update/', views.StudentProfileUpdateView.as_view(), name='student_profile_update'),
    path('student/recommendations/', views.all_recommendations, name='all_recommendations'),
    path('student/recommendation-explanation/', views.recommendation_explanation, name='recommendation_explanation'),
    path('student/preferences/update/', views.update_preferences, name='update_preferences'),
    
    # Landlord profile
    path('landlord-registrationlandlord_registration_success-success/', views.landlord_registration_success, name='landlord_registration_success'),
    path('landlord/profile/', views.LandlordProfileView.as_view(), name='landlord_profile'),
    path('landlord/profile/update/', views.LandlordProfileUpdateView.as_view(), name='landlord_profile_update'),
    path('landlord/profile/personal-info/', views.UpdatePersonalInfoView.as_view(), name='update_personal_info'),
    path('landlord/profile/picture/', views.UpdateProfilePictureView.as_view(), name='update_profile_picture'),
    path('landlord/verification-documents/', views.VerificationDocumentsView.as_view(), name='verification_documents'),
    path('landlord/verification/reapply/<int:pk>/', views.reapply_verification, name='reapply_verification'),
    
    # Admin verification
    path('admin/landlord/verification/', views.LandlordVerificationListView.as_view(), name='landlord_verification_list'),
    path('admin/landlord/verification/<int:pk>/', views.LandlordVerificationDetailView.as_view(), name='landlord_verification_detail'),
    path('admin/landlord/verify/<int:pk>/', views.verify_landlord, name='verify_landlord'),

    # Admin student management
    path('admin/students/', views.AdminStudentListView.as_view(), name='student_list'),
    path('admin/students/add/', views.AdminStudentCreateView.as_view(), name='student_add'),
    path('admin/students/<int:pk>/', views.AdminStudentDetailView.as_view(), name='student_detail'),
    path('admin/students/<int:pk>/update/', views.AdminStudentUpdateView.as_view(), name='student_update'),
    path('admin/students/<int:pk>/delete/', views.AdminStudentDeleteView.as_view(), name='student_delete'),

    # Export students
    path('admin/students/export/excel/', views.export_students_excel, name='export_students_excel'),
    path('admin/students/export/pdf/', views.export_students_pdf, name='export_students_pdf'),

    # Admin Hostel Management
    path('admin/hostels/', views.admin_hostel_list, name='admin_hostel_list'),
    path('admin/hostels/<int:pk>/', views.admin_hostel_detail, name='admin_hostel_detail'),
    path('admin/hostels/create/', views.admin_hostel_create, name='admin_hostel_create'),
    path('admin/hostels/<int:pk>/update/', views.admin_hostel_update, name='admin_hostel_update'),
    path('admin/hostels/<int:pk>/delete/', views.admin_hostel_delete, name='admin_hostel_delete'),
    
    # Password reset
    path('password-reset/', 
        auth_views.PasswordResetView.as_view(template_name='accounts/password_reset.html'),
        name='password_reset'),
    path('password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(template_name='accounts/password_reset_done.html'),
        name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(template_name='accounts/password_reset_confirm.html'),
        name='password_reset_confirm'),
    path('password-reset-complete/',
        auth_views.PasswordResetCompleteView.as_view(template_name='accounts/password_reset_complete.html'),
        name='password_reset_complete'),

    path('tenants/export/excel/', views.export_tenants_excel, name='export_tenants_excel'),
    path('tenants/export/pdf/', views.export_tenants_pdf, name='export_tenants_pdf'),

    # Admin landlord management
    path('admin/landlords/', views.admin_landlord_list, name='landlord_list'),
    path('admin/landlords/add/', views.admin_add_landlord, name='admin_add_landlord'),
    path('admin/landlords/<int:pk>/edit/', views.admin_edit_landlord, name='admin_edit_landlord'),
    path('admin/landlords/<int:pk>/delete/', views.admin_delete_landlord, name='admin_delete_landlord'),

]
