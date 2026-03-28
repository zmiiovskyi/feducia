from django.shortcuts import render

def main_page(request):
    return render(request, "dashboard/main_page.html")

def profile_page(request):
    return render(request, "dashboard/profile_page.html")

def about_view(request):
    return render(request, 'dashboard/about_us.html')

def contacts_view(request):
    return render(request, 'dashboard/contacts.html')