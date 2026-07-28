from django.shortcuts import redirect
from django.contrib import messages
from .models import UserProfile

class RoleCheckMiddleware:
    """Middleware to check user role for restricted URLs"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        response = self.get_response(request)
        return response
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        # Skip for admin/staff users
        if request.user.is_authenticated and request.user.is_staff:
            return None
        
        # Define URL patterns that require specific roles
        artist_urls = [
            '/create-release/',
            '/add-tracks/',
            '/publish-release/',
            '/edit-release/',
            '/delete-release/',
            '/delete-track/',
            '/upload-cover-art/',
            '/my-releases/',
            '/my-drafts/',
            '/my-pending/',
            '/analytics/',
        ]
        
        fan_urls = [
            '/fan/library/',
            '/fan/playlist/',
            '/fan/search/',
        ]
        
        path = request.path_info
        
        # Check if user is authenticated
        if request.user.is_authenticated:
            try:
                profile = UserProfile.objects.get(user=request.user)
                role = profile.role
            except UserProfile.DoesNotExist:
                # User doesn't have a profile
                if any(url in path for url in artist_urls + fan_urls):
                    messages.error(request, "Please create a profile first.")
                    return redirect('choose-profile')
                return None
            
            # Check artist-only URLs
            if any(url in path for url in artist_urls):
                if role != 'Artist':
                    messages.error(request, "Access denied. Only artists can access this page.")
                    if role == 'Fan':
                        return redirect('fanboard')
                    return redirect('index')
            
            # Check fan-only URLs
            if any(url in path for url in fan_urls):
                if role != 'Fan':
                    messages.error(request, "Access denied. Only fans can access this page.")
                    if role == 'Artist':
                        return redirect('artistboard')
                    return redirect('index')
        
        return None