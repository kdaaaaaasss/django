from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('users.urls')),
    path('support/', include('support.urls')),
    path('reviews/', include('reviews.urls')),
    path('notifications/', include('notifications.urls')),
    path('crm/', include('crm.urls')),
    path('', include('housing.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / 'static')
