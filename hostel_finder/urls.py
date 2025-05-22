from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('hostels/', include('hostels.urls')),
    path('payments/', include('payments.urls')),
    # path('chat/', include('chatbot.urls')),
    path('faqs/', include('faqs.urls')),
    path('bookings/', include('bookings.urls')),
    
    # Home page as placeholder for now
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)