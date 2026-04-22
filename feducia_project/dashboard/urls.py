from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.landing_view, name='landing'),
    path('profile/', views.profile_page, name='profile'),
    path('about/', views.about_view, name='about_page'),
    path('contacts/', views.contacts_view, name='contacts_page'),
    path('dashboard/', views.main_page, name='Main_Page'),
    path('password-reset/', views.password_reset_request, name='password_reset'),
    path('logout/', views.logout_view, name='logout'),
    path('delete-account/', views.delete_account_view, name='delete_account'),
    path(
        'change-password/',
        auth_views.PasswordChangeView.as_view(
            template_name='dashboard/change_password.html',
            success_url='/profile/'
        ),
        name='password_change'
    ),
    path('change-profile/', views.edit_profile_view, name='edit_profile'),
    path('guide/<int:guide_id>/', views.guide_view, name='guide'),
    path('reset/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),
    path('privacy/', views.privacy_view, name='private_policy'),
    path('terms/', views.terms_view, name='terms_of_use'),

    path('profile/upload-avatar/', views.upload_avatar_view, name='upload_avatar'),
    path('profile/delete-avatar/', views.delete_avatar_view, name='delete_avatar'),
]