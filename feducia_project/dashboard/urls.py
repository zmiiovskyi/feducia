from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.main_page, name='Main_Page'),
]