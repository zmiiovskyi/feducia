from django.urls import path
from . import views

urlpatterns = [
    path('', views.main_page, name='Main_Page'),
    path('about/', views.about_view, name='about_page'),
]