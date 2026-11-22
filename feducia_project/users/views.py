from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from feducia_project.ratelimit import rate_limit

User = get_user_model()

@rate_limit("login", limit=10, window=300)
def user_login(request):
   error = None
   username = ""

   if request.method == "POST":
       username = request.POST.get("username")
       password = request.POST.get("password")

       user = authenticate(request, username=username, password=password)

       if user is not None:
           login(request, user)
           return redirect("/dashboard/")
       else:
           error = "Incorrect username or password."

   return render(request, "users/login.html", {
       "error": error,
       "username": username,
   })

@rate_limit("signup", limit=10, window=3600)
def user_signup(request):
    error = None
    username = ""
    email = ""

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")

        if not username or not email or not password:
            error = "All fields are required."
        elif User.objects.filter(username=username).exists():
            error = "This username is already taken."
        elif User.objects.filter(email__iexact=email).exists():
            error = "This email is already registered."
        else:
            user = User(username=username, email=email)
            try:
                user.full_clean(exclude=["password"])
                validate_password(password, user)
            except ValidationError as e:
                error = " ".join(e.messages)
            else:
                user.set_password(password)
                user.save()
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                return redirect('/dashboard/')

    return render(request, "users/sign_up.html", {
       "error": error,
       "username": username,
       "email": email,
   })