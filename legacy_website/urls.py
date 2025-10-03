# In legacy_website/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static # This must be imported!

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('main_app.urls')),
]

# REMOVED: if settings.DEBUG:

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)