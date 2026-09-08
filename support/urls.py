from django.urls import path

from . import views

urlpatterns = [
    path('', views.ticket_list, name='ticket_list'),
    path('new/', views.ticket_new, name='ticket_new'),
    path('<int:pk>/', views.ticket_detail, name='ticket_detail'),
    path('<int:pk>/close/', views.ticket_close, name='ticket_close'),
]
