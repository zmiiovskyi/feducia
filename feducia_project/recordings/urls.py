from django.urls import path
from . import views

app_name = "recordings"

urlpatterns = [
    path('recording/', views.recording_view, name='record'),
    path('save-recording/', views.save_recording_view, name='save_recording'),
    path("analytics/<int:session_id>/", views.analytics_view, name="analytics"),
    path("loading/<int:session_id>/", views.loading_view, name="loading"),
     path("delete/<int:session_id>/", views.delete_session_view, name="delete_session"),
]