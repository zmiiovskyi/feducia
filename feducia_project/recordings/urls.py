from django.urls import path
from . import views

urlpatterns = [
    path('recording', views.recording, name='Recording'),
]