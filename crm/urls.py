from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='crm_dashboard'),
    path('moderation/', views.moderation, name='crm_moderation'),
    path('moderation/<int:pk>/<str:action>/', views.moderate_action, name='crm_moderate'),
    path('listings/', views.listings, name='crm_listings'),
    path('bookings/', views.bookings, name='crm_bookings'),
    path('bookings/<int:pk>/<str:action>/', views.booking_action, name='crm_booking_action'),
    path('tickets/', views.tickets, name='crm_tickets'),
    path('tickets/<int:pk>/', views.ticket_detail, name='crm_ticket'),
    path('reviews/', views.reviews, name='crm_reviews'),
    path('reviews/<int:pk>/<str:action>/', views.review_action, name='crm_review_action'),
    path('users/', views.users, name='crm_users'),
    path('users/<int:pk>/<str:action>/', views.user_action, name='crm_user_action'),
]
