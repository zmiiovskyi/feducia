from django.shortcuts import render

def recording(request):
    return render(request, "recordings/recording.html")
