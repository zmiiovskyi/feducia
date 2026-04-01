from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.views.decorators.cache import never_cache

@login_required
def main_page(request):
    return render(request, "dashboard/main_page.html")

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
                'fiducia.futurum@gmail.com',
                ['fiducia.futurum@gmail.com'],
                fail_silently=False,
            )
            messages.success(request, 'Message successfully sent!')
            return redirect('contacts')
        except Exception as e:
            messages.error(request, f'Error: {e}')

    return render(request, "dashboard/contacts.html")

def password_reset_view(request):
    return render(request, 'dashboard/password_reset.html')
    return render(request, 'dashboard/contacts.html')

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def delete_account_view(request):
    user = request.user
    user.delete()
    return redirect('Main_Page')