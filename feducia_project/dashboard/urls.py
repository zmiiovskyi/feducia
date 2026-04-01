from django.urls import path
from . import views

urlpatterns = [
    path('', views.main_page, name='Main_Page'),
    path('profile/', views.profile_page, name='profile'),
    path('about/', views.about_view, name='about_page'),
    path('contacts/', views.contacts_view, name='contacts_page'),
    path('dashboard/', views.main_page, name='Main_Page'),
    path('password-reset/', views.password_reset_view, name='password_reset'),
]