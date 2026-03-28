from django.urls import path
from . import views

urlpatterns = [
    path('', views.main_page, name='Main_Page'),
    path('contacts/', views.contacts_view, name='contacts_page'),
]