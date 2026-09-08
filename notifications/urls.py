from django.urls import path

from . import views

urlpatterns = [
    path('', views.notification_list, name='notifications'),
    path('read-all/', views.mark_all_read, name='notifications_read_all'),
]
