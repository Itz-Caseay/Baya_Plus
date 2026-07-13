from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from .models import *

# Create your views here.
# signup views function
def signup(request):
    if request.method == "POST":
        username = request.POST.get('username')
        fullname = request.POST.get('fullname')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        
        if password==password2:
            if User.objects.filter(email=email, username=username).exists():
                messages.error(request, "Email or Username already taken use another email")
                return redirect('signup')
            else:
                user = User.objects.create_user(
                    username=username,
                    fullname=fullname,
                    email=email,
                    password=password
                )
                login(request, user)
                return redirect('choose-profile')
        else:
            messages.error(request, "Password didnot match")
            return redirect('signup')
    return render(request, "auth/signup.html")

# signin views function
def login_user(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            # Check whether the user has created a profile
            try:
                profile = UserProfile.objects.get(user=user)

                messages.success(request, "Successfully logged in.")

                # Redirect according to profile role
                if profile.role == "Artist":
                    return redirect("artistboard")

                elif profile.role == "Fan":
                    return redirect("fanboard")

                # Fallback
                return redirect("index")

            except UserProfile.DoesNotExist:
                messages.info(request, "Please create your profile before continuing.")
                return redirect("choose-profile")

        else:
            messages.error(request, "Invalid username or password.")
            return redirect("login")

    return render(request, "auth/login.html")

@login_required(login_url='login')
def logout_user(request):
    logout(request)
    messages.success(request, "Successfully Logged out")
    return redirect('login')

def choose_profile(request):
    if request.method == "POST":
        role = request.POST.get("role")

        if role == "Artist":
            artist_name = request.POST.get("artist_name")

            if UserProfile.objects.filter(artist_name=artist_name).exists():
                messages.error(request, "Artist name denied. Already used by another artist")
                return redirect("choose-profile")

            UserProfile.objects.create(
                user = request.user,
                role=role,
                artist_name=artist_name
            )

            messages.success(request, "Artist account created successfully")
            return redirect("artistboard")

        elif role == "Fan":
            UserProfile.objects.create(
                role=role,
                user = request.user,
            )

            messages.success(request, "Fan account created successfully")
            return redirect("fanboard")

    return render(request, "auth/choose-profile.html")

def fanboard(request):
    profile = UserProfile.objects.get(user=request.user)
    return HttpResponse(f"""
                        <h3>{request.user.username} Welcom to your Artist page</h3> <h3>Role: {profile.role}</h3>"""
                        )

def artistboard(request):
    profile = UserProfile.objects.get(user=request.user)
    return HttpResponse(f"""
                        <h3>{request.user.username} Welcom to your Fan page</h3> <h3>Role: {profile.role}</h3>"""
                        )