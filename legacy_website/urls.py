# legacy_website/urls.py (Project Root)

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from main_app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('main_app.urls')),
    path('webhooks/instagram/', views.instagram_webhook, name='instagram_webhook'),
]

# CRITICAL: The following lines are ONLY for local development with DEBUG=True.
# These fix the 404 image errors by telling Django how to serve media files locally.
if settings.DEBUG:
    # Serve STATIC files (CSS, JS)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    # Serve MEDIA files (User uploads/Profile Icons)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)