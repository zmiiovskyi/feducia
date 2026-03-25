from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, get_user_model

User = get_user_model()

def user_login(request):
   error = None
   username = ""

   if request.method == "POST":
       username = request.POST.get("username")
       password = request.POST.get("password")

       user = authenticate(request, username=username, password=password)

       if user is not None:
           login(request, user)
           return redirect("/")
       else:
           error = "Incorrect username or password."

   return render(request, "users/login.html", {
       "error": error,
       "username": username,
   })

def user_signup(request):
    error = None
    username = ""
    email = ""

    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")


        if User.objects.filter(username=username).exists():
            error = "This username is already taken."
        elif User.objects.filter(email=email).exists():
            error = "This email is already registered."
        else:
            user = User.objects.create_user(username=username, email=email, password=password)
            login(request, user)
            return redirect("/")

    print(error)

    return render(request, "users/sign_up.html", {
       "error": error,
       "username": username,
       "email": email,
   })