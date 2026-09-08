from django.urls import path

from . import views, views_dashboard

urlpatterns = [
    path('', views.index, name='index'),
    path('catalog/', views.catalog, name='catalog'),
    path('catalog/add/', views.housing_add, name='housing_add'),
    path('catalog/<int:pk>/', views.housing_detail, name='housing_detail'),
    path('catalog/<int:pk>/edit/', views.housing_edit, name='housing_edit'),
    path('catalog/<int:pk>/submit/', views.housing_submit, name='housing_submit'),
    path('catalog/<int:pk>/delete/', views.housing_delete, name='housing_delete'),
    path('catalog/<int:pk>/book/', views.booking_create, name='booking_create'),
    path('catalog/<int:pk>/favorite/', views_dashboard.favorite_toggle, name='favorite_toggle'),
    path('booking/<int:pk>/<str:action>/', views.booking_action, name='booking_action'),
    path('service/', views.service, name='service'),
    path('help/', views.help_center, name='support_public'),
    path('styleguide/', views.styleguide, name='styleguide'),


    path('dashboard/', views_dashboard.dashboard, name='dashboard'),
    path('dashboard/bookings/', views_dashboard.my_bookings, name='my_bookings'),
    path('dashboard/requests/', views_dashboard.booking_requests, name='booking_requests'),
    path('dashboard/listings/', views_dashboard.my_listings, name='my_listings'),
    path('dashboard/reviews/', views_dashboard.my_reviews, name='my_reviews'),
    path('dashboard/favorites/', views_dashboard.favorites, name='favorites'),
    path('dashboard/calendar/', views_dashboard.host_calendar, name='host_calendar'),
    path('dashboard/earnings/', views_dashboard.earnings, name='earnings'),
    path('dashboard/settings/', views_dashboard.settings_view, name='dashboard_settings'),
]
