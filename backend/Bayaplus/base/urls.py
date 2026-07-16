from django.urls import path
from .views import *

urlpatterns = [
    path('login/', login_user, name="login"),
    path('signup/', signup, name="signup"),
    path('logout/', logout_user, name="logout"),
    path('choose-profile/', choose_profile, name="choose-profile"),
    path('fanboard/', fanboard, name="fanboard"),
    path('artistboard/', artistboard, name="artistboard"),
    path('activate/<uidb64>/<token>/', activate, name='activate'),
   path('create-release/', create_release, name='create_release'),
   # In urls.py
    path('upload-cover-art/<int:release_id>/', upload_cover_art, name='upload_cover_art'),
    
    # Add tracks to release
    path('add-tracks/<int:release_id>/', add_tracks, name='add_tracks'),
    
    # Publish/Submit release for review
    path('publish-release/<int:release_id>/', publish_release, name='publish_release'),
    
    # Edit release
    path('edit-release/<int:release_id>/', edit_release, name='edit_release'),
    
    # Delete release
    path('delete-release/<int:release_id>/', delete_release, name='delete_release'),
    
    # Delete track from release
    path('delete-track/<int:release_id>/<int:track_id>/', delete_track, name='delete_track'),
    
    # ==================== RELEASE VIEWING URLs ====================
    # View release detail (public)
    # path('release/<int:release_id>/', release_detail, name='release_detail'),
    
    # View all releases by an artist
    # path('artist/<str:username>/releases/', artist_releases, name='artist_releases'),
    
    # View all releases (browse)
    # path('releases/', all_releases, name='all_releases'),
    
    # View trending/popular releases
    # path('releases/trending/', trending_releases, name='trending_releases'),
    
    # ==================== INTERACTION URLs ====================
    # Like a release
    # path('like-release/<int:release_id>/', like_release, name='like_release'),
    
    # Add comment to release
    # path('comment-release/<int:release_id>/', add_comment, name='add_comment'),
    
    # Delete comment
    # path('delete-comment/<int:comment_id>/', delete_comment, name='delete_comment'),
    
    # ==================== ADMIN REVIEW URLs ====================
    # View all pending releases (admin only)
    path('admin/pending-releases/', admin_pending_releases, name='admin_pending_releases'),
    
    # Review a specific release (admin only)
    path('admin/review-release/<int:release_id>/', admin_review_release, name='admin_review_release'),
    
    # View all releases for admin
    # path('admin/all-releases/', admin_all_releases, name='admin_all_releases'),
    
    # ==================== ARTIST MANAGEMENT URLs ====================
    # View artist's all releases
    # path('my-releases/', my_releases, name='my_releases'),
    
    # View artist's drafts
    # path('my-drafts/', my_drafts, name='my_drafts'),
    
    # View artist's pending releases
    # path('my-pending/', my_pending_releases, name='my_pending_releases'),
    
    # ==================== TEST URL ====================
    # path('test-email/', test_email, name='test_email'),
]
