"""
URL configuration for feducia_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, include
from django.contrib import admin
from django.views.generic import RedirectView

from .media import protected_media_view
from .ratelimit import rate_limit

urlpatterns = [
    path("admin/login/", rate_limit("admin_login", limit=10, window=300)(admin.site.login)),
    path("admin/", admin.site.urls),
    path("media/<path:path>", protected_media_view, name="media"),
    path("", include("users.urls")),
    path('', include('dashboard.urls')),
    path("", include("recordings.urls")),
    path("accounts/", include("allauth.urls")),
]
