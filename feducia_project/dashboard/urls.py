from django.urls import path
from . import views
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('', views.main_page, name='Main_Page'),
    path('profile/', views.profile_page, name='profile'),
    path('about/', views.about_view, name='about_page'),
    path('contacts/', views.contacts_view, name='contacts_page'),
    path('dashboard/', views.main_page, name='Main_Page'),
    path('password-reset/', views.password_reset_view, name='password_reset'),
    path('logout/', views.logout_view, name='logout'),
    path('delete-account/', views.delete_account_view, name='delete_account'),
    path('change-password/', auth_views.PasswordChangeView.as_view(
        template_name='dashboard/change_password.html',
        success_url='/profile/'
    ), name='password_change'),
    path('change-profile/', views.edit_profile_view, name='edit_profile'),

]