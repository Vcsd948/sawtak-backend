from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # ✅ On inclut les URLs de nos différentes applications
    path('api/auth/', include('apps.users.urls')),
    path('api/claims/', include('apps.claims.urls')),
    path('api/attachments/', include('apps.attachments.urls')),
    path('api/notifications/', include('apps.notifications.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)