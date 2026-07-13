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
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        try:
            user = authenticate(request, email=email, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, "Successfully logged In")
                return redirect('index')
            
            else:
                messages.error(request, "Invalid Credentials")
                return redirect('login')
        
        except Exception as e:
            
            messages.error(request, {'error':e})
    return render(request, "auth/login.html")


@login_required(login_url='login')
def logout_user(request):
    logout(request)
    messages.success(request, "Successfully Logged out")
    return redirect('login')

def choose_profile(request):
    if request.method == 'POST':
        role = request.POST['role']
        if role == "artist":
            artist_name = request.POST['artist_name']
            
            
        elif role == "fan":
            messages.success(request, "Fan account created successfully")
            return redirect('fanboard')
    return HttpResponse("Artist or Fan?")