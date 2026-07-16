from django.contrib import admin
from .models import *

# Register your models here.

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'fullname', 'date_joined', 'is_active']
    search_fields = ['username', 'email', 'fullname']
    list_filter = ['is_active', 'is_staff']

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'artist_name', 'email_verified', 'payment_verified']
    search_fields = ['user__username', 'artist_name']
    list_filter = ['role', 'email_verified', 'payment_verified']

@admin.register(Release)
class ReleaseAdmin(admin.ModelAdmin):
    list_display = ['title', 'artist', 'release_type', 'status', 'release_date', 'is_public']
    search_fields = ['title', 'artist__username']
    list_filter = ['release_type', 'status', 'is_public', 'is_featured']

@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ['title', 'release', 'track_number', 'is_explicit']
    search_fields = ['title', 'release__title']

@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ['user', 'release', 'track', 'created_at']
    
@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['user', 'release', 'content_preview', 'created_at', 'is_approved']
    search_fields = ['content', 'user__username']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content

@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'is_public', 'created_at']
    search_fields = ['name', 'user__username']
    
# admin.site.register(Comment)