import logging
import uuid

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from feducia_project.ratelimit import rate_limit
from .forms import AvatarForm, ProfileUpdateForm
from recordings.models import SpeechSession
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives, send_mail
from django.http import JsonResponse
from .models import Profile

User = get_user_model()
logger = logging.getLogger(__name__)

def landing_view(request):
    return render(request, 'dashboard/landing.html')

@login_required
def main_page(request):
    all_sessions = SpeechSession.objects.filter(user=request.user).order_by('-created_at')
    context = {
        'sessions': all_sessions
    }
    return render(request, "dashboard/main_page.html", context)

@never_cache
@login_required
def profile_page(request):
    return render(request, "dashboard/profile_page.html")

def about_view(request):
    return render(request, 'dashboard/about_us.html')

@rate_limit("contacts", limit=5, window=3600)
def contacts_view(request):
    if request.method == 'POST':
        # прибираємо переноси рядків, бо name йде в тему листа
        name = ' '.join(request.POST.get('name', '').split())[:100]
        email = request.POST.get('email')
        message = request.POST.get('message')

        subject = f"New message from {name}"
        full_content = f"Sender: {name}\nEmail: {email}\n\nMessage:\n{message}"

        try:
            send_mail(
                subject,
                full_content,
                'fiducia.futurum@gmail.com',
                ['fiducia.futurum@gmail.com'],
                fail_silently=False,
            )
            messages.success(request, 'Message successfully sent!')
            return redirect('contacts_page')
        except Exception:
            logger.exception("Contact email failed")
            messages.error(request, 'Could not send the message. Please try again later.')
    return render(request, "dashboard/contacts.html")


@login_required
def edit_profile_view(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated!")
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=request.user)
    return render(request, 'dashboard/edit_profile.html', {'form': form})

def guide_view(request, guide_id):
    if 1 <= guide_id <= 11:
        return render(request, f'dashboard/guides/guide_{guide_id}.html')
    else:
        return redirect('Main_Page')

@require_POST
def logout_view(request):
    logout(request)
    return redirect('landing')

@require_POST
@login_required
def delete_account_view(request):
    user = request.user
    user.delete()
    return redirect('landing')

@rate_limit("password_reset", limit=5, window=3600)
def password_reset_request(request):
    message = None
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        users = User.objects.filter(email__iexact=email, is_active=True) if email else []
        for user in users:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            relative_link = reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
            link = request.build_absolute_uri(relative_link)
            html_content = render_to_string("emails/email_message.html", {
                "user": user.username,
                "reset_link": link
            })
            email_msg = EmailMultiAlternatives(
                subject="Fiducia Password Reset",
                body=f"Reset link: {link}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            email_msg.attach_alternative(html_content, "text/html")
            try:
                email_msg.send(fail_silently=False)
            except Exception:
                logger.exception("Password reset email failed")
        # однакова відповідь, щоб не розкривати, чи існує акаунт
        message = "If this email is registered, we have sent you a reset link."
    return render(request, "dashboard/password_reset.html", {"message": message})

@never_cache
def password_reset_confirm(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid, is_active=True)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            new_pass = request.POST.get('password', '')
            confirm_pass = request.POST.get('confirm_password', '')
            if new_pass == confirm_pass:
                try:
                    validate_password(new_pass, user)
                except ValidationError as e:
                    return render(request, 'dashboard/email_change_password.html', {'error': ' '.join(e.messages)})
                user.set_password(new_pass)
                user.save()
                if request.user == user:
                    update_session_auth_hash(request, user)
                messages.success(request, "Password updated!")
                return redirect('landing')
            else:
                return render(request, 'dashboard/email_change_password.html', {'error': 'No match.'})
        return render(request, 'dashboard/email_change_password.html')
    else:
        return render(request, "dashboard/password_reset.html", {"message": "Invalid link."})

def privacy_view(request):
    return render(request, 'dashboard/private_policy.html')

def terms_view(request):
    return render(request, 'dashboard/terms_of_use.html')

@login_required
def upload_avatar_view(request):
    if request.method == 'POST' and request.FILES.get('avatar'):
        form = AvatarForm(request.POST, request.FILES)
        if not form.is_valid():
            return JsonResponse({'status': 'error', 'message': form.errors['avatar'][0]}, status=400)

        avatar = form.cleaned_data['avatar']
        extension = avatar.name.rsplit('.', 1)[-1].lower()
        avatar.name = f"{uuid.uuid4().hex}.{extension}"

        profile, created = Profile.objects.get_or_create(user=request.user)
        old_avatar = profile.avatar.name
        profile.avatar = avatar
        profile.save()
        if old_avatar:
            profile.avatar.storage.delete(old_avatar)
        return JsonResponse({'status': 'success', 'avatar_url': profile.avatar.url})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

@login_required
def delete_avatar_view(request):
    if request.method == 'POST':
        profile, created = Profile.objects.get_or_create(user=request.user)
        if profile.avatar:
            profile.avatar.delete(save=True)
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)