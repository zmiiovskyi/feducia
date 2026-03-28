from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def main_page(request):
    return render(request, "dashboard/main_page.html")