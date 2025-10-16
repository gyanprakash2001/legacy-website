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
    path('auth/instagram/connect/', views.instagram_auth_start, name='instagram_auth_start'),
    path('auth/instagram/callback/', views.instagram_auth_callback, name='instagram_auth_callback'),
    path('auth/callback', views.instagram_auth_callback, name='instagram_auth_callback'),
    path('auth/callback/', views.instagram_auth_callback, name='instagram_auth_callback_slash'),
    path('privacy-policy/', views.privacy_policy_view, name='privacy_policy'),
    path('terms-of-service/', views.terms_of_service_view, name='terms_of_service'),
]

# CRITICAL: The following lines are ONLY for local development with DEBUG=True.
# These fix the 404 image errors by telling Django how to serve media files locally.
if settings.DEBUG:
    # Serve STATIC files (CSS, JS)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    # Serve MEDIA files (User uploads/Profile Icons)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)