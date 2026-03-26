from django.shortcuts import render

def main_page(request):
    return render(request, "dashboard/main_page.html")