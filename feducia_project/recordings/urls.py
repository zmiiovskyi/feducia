from django.urls import path
from . import views

app_name = "recordings"

urlpatterns = [
    path('recording/', views.recording_view, name='record'),
    path('save-recording/', views.save_recording_view, name='save_recording'),
    path("analytics/", views.analytics_view, name="analytics"),
    path("loading/", views.loading_view, name="loading"),
]