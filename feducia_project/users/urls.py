from django.urls import path
from .views import UserLoginView

urlpatterns = [
    path("", UserLoginView.as_view(), name="login"),
]