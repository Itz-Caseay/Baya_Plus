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
    path('admin/pending-releases/', admin_pending_releases, name='admin_pending_releases'),
    path('admin/review-release/<int:release_id>/', admin_review_release, name='admin_review_release'),
]
