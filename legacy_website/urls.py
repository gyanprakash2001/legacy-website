# In legacy_website/urls.py

from django.contrib import admin
from django.urls import path, include

# Cloudinary handles media URLs automatically. WhiteNoise handles static files.
# No need for complex logic or django.conf.urls.static imports in production.

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('main_app.urls')),
]

# The following lines are ONLY for local development with DEBUG=True.
# You can delete these lines entirely, or comment them out, to ensure
# Cloudinary takes over in production.
# from django.conf import settings
# from django.conf.urls.static import static
# if settings.DEBUG:
#     urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)