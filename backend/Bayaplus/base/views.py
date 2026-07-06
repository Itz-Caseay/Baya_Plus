from django.shortcuts import render, redirect, get_object_or_404
from .models import *
from django.contrib.auth import authenticate, login, logout

# Create your views here.
def dashboard(request):
    return render(request, "./index.html")