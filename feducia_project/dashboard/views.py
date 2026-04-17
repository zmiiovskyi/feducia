from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.views.decorators.cache import never_cache
from .forms import ProfileUpdateForm
from recordings.models import SpeechSession
from django.contrib.auth import get_user_model
from django.contrib import messages


User = get_user_model()

def landing_view(request):
    if request.user.is_authenticated:
        return redirect('Main_Page')
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

def contacts_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')

        subject = f"New message from {name}"
        full_content = f"Sender: {name}\nEmail: {email}\n\nMessage:\n{message}"

        try:
            send_mail(
                subject,
                full_content,
                settings.EMAIL_HOST_USER,
                ['fiducia.futurum@gmail.com'],
                fail_silently=False,
            )
            messages.success(request, 'Message successfully sent!')
            return redirect('contacts_page')
        except Exception as e:
            messages.error(request, f'Mail Error: {str(e)}')
    return render(request, "dashboard/contacts.html")

@never_cache
@login_required
def profile_page(request):
    return render(request, "dashboard/profile_page.html")

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

def logout_view(request):
    logout(request)
    return redirect('landing')

@login_required
def delete_account_view(request):
    user = request.user
    user.delete()
    return redirect('landing')

def password_reset_request(request):
    message = None
    if request.method == "POST":
        email = request.POST.get("email")
        try:
            user = User.objects.get(email=email)
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
                from_email=settings.EMAIL_HOST_USER,
                to=[email]
            )
            email_msg.attach_alternative(html_content, "text/html")
            email_msg.send(fail_silently=False)
            message = "Success! Check your email."
        except User.DoesNotExist:
            message = "Error: User not found."
        except Exception as e:
            message = f"SMTP Error: {str(e)}"
    return render(request, "dashboard/password_reset.html", {"message": message})

def password_reset_confirm(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            new_pass = request.POST.get('password')
            confirm_pass = request.POST.get('confirm_password')
            if new_pass == confirm_pass:
                if len(new_pass) >= 8:
                    user.set_password(new_pass)
                    user.save()
                    update_session_auth_hash(request, user)
                    messages.success(request, "Password updated!")
                    return redirect('landing')
                else:
                    return render(request, 'dashboard/email_change_password.html', {'error': 'Min 8 chars.'})
            else:
                return render(request, 'dashboard/email_change_password.html', {'error': 'No match.'})
        return render(request, 'dashboard/email_change_password.html')
    else:
        return render(request, "dashboard/password_reset.html", {"message": "Invalid link."})

def privacy_view(request):
    return render(request, 'dashboard/private_policy.html')

def terms_view(request):
    return render(request, 'dashboard/terms_of_use.html')