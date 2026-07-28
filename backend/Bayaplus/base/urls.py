from django.urls import path
from . import views


urlpatterns = [
    # ==================== MAIN INDEX ====================
    path('', views.index, name='index'),  # ← ADD THIS - This is the homepage
    
    # ==================== AUTHENTICATION URLs ====================
    path('signup/', views.signup, name='signup'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),
    path('choose-profile/', views.choose_profile, name='choose-profile'),
    
    # ==================== DASHBOARD URLs ====================
    path('fanboard/', views.fanboard, name='fanboard'),
    path('artistboard/', views.artistboard, name='artistboard'),
    
    # ==================== FAN URLs ====================
    path('fan/library/', views.fan_library, name='fan_library'),
    path('fan/playlist/', views.fan_playlist, name='fan_playlist'),
    path('fan/playlist/<int:playlist_id>/', views.fan_playlist, name='fan_playlist_detail'),
    path('fan/search/', views.fan_search, name='fan_search'),
    
    # ==================== RELEASE MANAGEMENT URLs ====================
    path('create-release/', views.create_release, name='create_release'),
    path('add-tracks/<int:release_id>/', views.add_tracks, name='add_tracks'),
    path('publish-release/<int:release_id>/', views.publish_release, name='publish_release'),
    path('edit-release/<int:release_id>/', views.edit_release, name='edit_release'),
    path('delete-release/<int:release_id>/', views.delete_release, name='delete_release'),
    path('delete-track/<int:release_id>/<int:track_id>/', views.delete_track, name='delete_track'),
    path('upload-cover-art/<int:release_id>/', views.upload_cover_art, name='upload_cover_art'),
    
    # ==================== RELEASE VIEWING URLs ====================
    path('release/<int:release_id>/', views.release_detail, name='release_detail'),
    path('releases/', views.all_releases, name='all_releases'),
    path('artist/<str:username>/releases/', views.artist_releases, name='artist_releases'),
    
    # ==================== ARTIST MANAGEMENT URLs ====================
    path('my-releases/', views.my_releases, name='my_releases'),
    path('my-drafts/', views.my_drafts, name='my_drafts'),
    path('my-pending/', views.my_pending_releases, name='my_pending_releases'),
    
    # ==================== ANALYTICS URLs ====================
    path('analytics/', views.analytics, name='analytics'),
    path('analytics/<int:release_id>/', views.release_analytics, name='release_analytics'),
    
    # ==================== INTERACTION URLs ====================
    path('like-release/<int:release_id>/', views.like_release, name='like_release'),
    path('like-track/<int:track_id>/', views.like_track, name='like_track'),
    path('comment-release/<int:release_id>/', views.add_comment, name='add_comment'),
    path('delete-comment/<int:comment_id>/', views.delete_comment, name='delete_comment'),
    
    # ==================== SOCIAL URLs ====================
    path('follow/<str:username>/', views.follow_artist, name='follow_artist'),
    path('following/', views.following_list, name='following_list'),
    path('followers/<str:username>/', views.followers_list, name='followers_list'),
    
    # ==================== STAFF/ADMIN URLs ====================
    path('staff/pending/', views.admin_pending_releases, name='admin_pending_releases'),
    path('staff/review/<int:release_id>/', views.admin_review_release, name='admin_review_release'),
    path('staff/all/', views.admin_all_releases, name='admin_all_releases'),
    
    # ==================== SETTINGS URLs ====================
    path('settings/profile/', views.profile_settings, name='profile_settings'),
    
    # ==================== TEST URL ====================
    path('test-email/', views.test_email, name='test_email'),
    path('test-admin-email/', views.test_admin_email, name='test_admin_email'),
    
    # Admin URLs
    path('staff/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('staff/profile/', views.admin_profile, name='admin_profile'),
    path('staff/users/', views.admin_all_users, name='admin_all_users'),
    path('staff/user/<int:user_id>/', views.admin_user_detail, name='admin_user_detail'),
    path('staff/pending/', views.admin_pending_releases, name='admin_pending_releases'),
    path('staff/review/<int:release_id>/', views.admin_review_release, name='admin_review_release'),
    path('staff/all/', views.admin_all_releases, name='admin_all_releases'),
]