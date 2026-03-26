from django.urls import path
from . import views

app_name = "recordings"

urlpatterns = [
    path("", views.recording, name="record"),
]