from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # Student URLs
    path('student/payments/', views.student_payments, name='student_payments'),
    path('student/invoice/<int:invoice_id>/', views.invoice_detail, name='invoice_detail'),
    path('landlord/export-pdf/', views.export_payments_pdf, name='export_payments_pdf'),
    path('landlord/export-excel/', views.export_payments_excel, name='export_payments_excel'),

    # Landlord URLs
    path('landlord/payments/', views.landlord_payments, name='landlord_payments'),
    path('landlord/confirm-payment/<int:payment_id>/', views.confirm_payment, name='confirm_payment'),
    path('landlord/create-invoice/<int:booking_id>/', views.create_invoice, name='create_invoice'),
    
    # Admin URLs
    path('admin/payments/', views.admin_payments, name='admin_payments'),
]