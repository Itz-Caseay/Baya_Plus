from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.core.mail import EmailMessage, send_mail
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives, send_mail
from django.contrib.auth.tokens import default_token_generator
from .utils import *
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from datetime import timedelta, datetime
import re
from .models import *
import logging
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncDate, TruncMonth
import json
from django.core.paginator import Paginator


logger = logging.getLogger(__name__)

# Add this decorator to check artist role
def artist_required(view_func):
    """Decorator to check if user has an Artist profile"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        try:
            profile = UserProfile.objects.get(user=request.user)
            if profile.role != 'Artist':
                messages.error(request, "Access denied. Only artists can access this page.")
                if profile.role == 'Fan':
                    return redirect('fanboard')
                return redirect('index')
        except UserProfile.DoesNotExist:
            messages.error(request, "Please create a profile first.")
            return redirect('choose-profile')
        
        return view_func(request, *args, **kwargs)
    return wrapper

# Add this decorator to check fan role
def fan_required(view_func):
    """Decorator to check if user has a Fan profile"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        try:
            profile = UserProfile.objects.get(user=request.user)
            if profile.role != 'Fan':
                messages.error(request, "Access denied. Only fans can access this page.")
                if profile.role == 'Artist':
                    return redirect('artistboard')
                return redirect('index')
        except UserProfile.DoesNotExist:
            messages.error(request, "Please create a profile first.")
            return redirect('choose-profile')
        
        return view_func(request, *args, **kwargs)
    return wrapper



def test_admin_email(request):
    """Test sending email to admins"""
    try:
        from django.core.mail import send_mail
        from django.conf import settings
        
        send_mail(
            'Test Admin Email from BayaPlus',
            'This is a test email to verify admin email configuration.',
            settings.ADMIN_EMAIL_FROM,
            settings.ADMIN_EMAILS,
            fail_silently=False,
        )
        return HttpResponse(f"✅ Test email sent successfully to: {', '.join(settings.ADMIN_EMAILS)}")
    except Exception as e:
        return HttpResponse(f"❌ Test email failed: {str(e)}")

def test_email(request):
    try:
        send_mail(
            'Test Email from BayaPlus',
            'This is a test email to verify email configuration.',
            settings.DEFAULT_FROM_EMAIL,
            ['your-test-email@gmail.com'],  # Replace with your email
            fail_silently=False,
        )
        return HttpResponse("✅ Test email sent successfully! Check your inbox.")
    except Exception as e:
        return HttpResponse(f"❌ Test email failed: {str(e)}")


def index(request):
    """Main landing page dashboard"""
    # Get all published releases
    releases = Release.objects.filter(status='published', is_public=True).order_by('-release_date')
    
    # Get trending releases (by plays/likes)
    trending = Release.objects.filter(status='published', is_public=True).order_by('-total_plays', '-total_likes')[:10]
    
    # Get recent releases
    recent = Release.objects.filter(status='published', is_public=True).order_by('-created_at')[:12]
    
    # Get featured releases
    featured = Release.objects.filter(status='published', is_public=True, is_featured=True)[:5]
    
    # Get top tracks
    top_tracks = Track.objects.filter(release__status='published', release__is_public=True).order_by('-plays')[:10]
    
    # Get random releases for "Made for you" section
    import random
    all_releases = list(Release.objects.filter(status='published', is_public=True))
    random.shuffle(all_releases)
    made_for_you = all_releases[:8]
    
    context = {
        'releases': releases,
        'trending': trending,
        'recent': recent,
        'featured': featured,
        'top_tracks': top_tracks,
        'made_for_you': made_for_you,
        'user': request.user,
    }
    
    return render(request, "pages/index.html", context)
def signup(request):
    if request.method == "POST":
        username = request.POST.get('username')
        fullname = request.POST.get('fullname')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        
        if password == password2:
            if User.objects.filter(email=email).exists():
                messages.error(request, "Email already taken. Use another email")
                return redirect('signup')
            if User.objects.filter(username=username).exists():
                messages.error(request, "Username already taken. Use another username")
                return redirect('signup')
            else:
                try:
                    user = User.objects.create_user(
                        username=username,
                        fullname=fullname,
                        email=email,
                        password=password
                    )
                    user.is_active = False
                    user.save()
                    
                    # Generate verification link
                    current_site = get_current_site(request)
                    uid = urlsafe_base64_encode(force_bytes(user.pk))
                    token = default_token_generator.make_token(user)
                    verification_link = f"http://{current_site.domain}/bayaplus/activate/{uid}/{token}/"
                    
                    print("\n" + "="*60)
                    print("🔗 VERIFICATION LINK:")
                    print(verification_link)
                    print("="*60 + "\n")
                    
                    # Try to send email
                    try:
                        mail_subject = 'Activate Your BayaPlus Account'
                        html_message = render_to_string('auth/acc_active_email.html', {
                            'user': user,
                            'domain': current_site.domain,
                            'uid': uid,
                            'token': token,
                        })
                        
                        # Check if using console backend
                        if settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend':
                            email_message = EmailMessage(
                                mail_subject,
                                html_message,
                                'BayaPlus <noreply@bayaplus.com>',
                                [email]
                            )
                            email_message.content_subtype = "html"
                            email_message.send()
                            print(f"✅ Email sent to console")
                        else:
                            # SMTP - with better error handling
                            try:
                                email_message = EmailMessage(
                                    mail_subject,
                                    html_message,
                                    settings.DEFAULT_FROM_EMAIL,
                                    [email]
                                )
                                email_message.content_subtype = "html"
                                email_message.send()
                                print(f"✅ Email sent successfully to {email}")
                            except Exception as smtp_error:
                                print(f"❌ SMTP Error: {str(smtp_error)}")
                                raise
                        
                        return render(request, "auth/registration_success.html", {
                            'email': email,
                            'verification_link': verification_link,
                        })
                        
                    except Exception as e:
                        print(f"❌ Email sending failed: {str(e)}")
                        return render(request, "auth/registration_error.html", {
                            'error_message': str(e),
                            'email': email,
                            'verification_link': verification_link,
                        })
                    
                except Exception as e:
                    messages.error(request, f"Error creating account: {str(e)}")
                    return redirect('signup')
        else:
            messages.error(request, "Passwords did not match")
            return redirect('signup')
    return render(request, "auth/signup.html")

def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        
        # Update the UserProfile to mark email as verified
        try:
            profile = UserProfile.objects.get(user=user)
            profile.email_verified = True
            profile.save()
        except UserProfile.DoesNotExist:
            pass
        
        return HttpResponse("""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; text-align: center; }
                    h2 { color: #4CAF50; }
                    .btn { display: inline-block; padding: 10px 20px; background: #4CAF50; color: white; text-decoration: none; border-radius: 5px; }
                </style>
            </head>
            <body>
                <h2>✅ Email Verified Successfully!</h2>
                <p>Your BayaPlus account has been activated.</p>
                <p>You can now login and start exploring BayaPlus.</p>
                <br>
                <a href="/login/" class="btn">Login to BayaPlus</a>
            </body>
            </html>
        """)
    else:
        return HttpResponse("""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; text-align: center; }
                    h2 { color: #f44336; }
                </style>
            </head>
            <body>
                <h2>❌ Invalid Verification Link</h2>
                <p>The activation link is invalid or has expired.</p>
                <p>Please <a href="/bayaplus/signup/">sign up</a> again.</p>
            </body>
            </html>
        """)

def login_user(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if not user.is_active:
                messages.error(request, "Account is not activated. Please check your email for verification link.")
                return redirect("login")
            
            login(request, user)

            try:
                profile = UserProfile.objects.get(user=user)

                if not profile.email_verified:
                    messages.warning(request, "Your email is not verified. Please check your inbox for the verification link.")
                
                messages.success(request, f"Welcome back, {user.username}!")

                if profile.role == "Artist":
                    return redirect("index")
                elif profile.role == "Fan":
                    return redirect("index")
                else:
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
    if not request.user.is_authenticated:
        messages.error(request, "Please login first.")
        return redirect('login')
    
    if UserProfile.objects.filter(user=request.user).exists():
        messages.error(request, "You already have a profile")
        return redirect('index')
    
    if request.method == "POST":
        role = request.POST.get("role")

        if role == "Artist":
            artist_name = request.POST.get("artist_name")
            
            if not artist_name:
                messages.error(request, "Artist name is required.")
                return redirect("choose-profile")

            if UserProfile.objects.filter(artist_name=artist_name).exists():
                messages.error(request, "Artist name already taken. Choose another")
                return redirect("choose-profile")

            UserProfile.objects.create(
                user=request.user,
                role=role,
                artist_name=artist_name,
                email_verified=request.user.is_active
            )

            messages.success(request, f"Artist account '{artist_name}' created successfully!")
            return redirect("artistboard")

        elif role == "Fan":
            UserProfile.objects.create(
                role=role,
                user=request.user,
                email_verified=request.user.is_active
            )

            messages.success(request, "Fan account created successfully!")
            return redirect("fanboard")
        else:
            messages.error(request, "Please select a valid role.")
            return redirect("choose-profile")

    return render(request, "auth/choose-profile.html")

@login_required(login_url='login')
def fanboard(request):
    """Fan dashboard - only accessible by users with Fan role"""
    # Check if user has a profile
    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        messages.error(request, "Please create a profile first.")
        return redirect('choose-profile')
    
    # Check if user has the Fan role
    if profile.role != 'Fan':
        messages.error(request, "Access denied. Only fans can access this page.")
        # Redirect based on their actual role
        if profile.role == 'Artist':
            return redirect('artistboard')
        else:
            return redirect('index')
    
    # Get fan-specific data
    followed_artists = Follow.objects.filter(follower=request.user).values_list('following', flat=True)
    followed_releases = Release.objects.filter(
        artist__in=followed_artists,
        status='published',
        is_public=True
    ).order_by('-release_date')[:10]
    
    trending = Release.objects.filter(
        status='published', 
        is_public=True
    ).order_by('-total_plays', '-total_likes')[:8]
    
    liked_releases = Like.objects.filter(user=request.user, release__isnull=False).select_related('release')
    liked_tracks = Like.objects.filter(user=request.user, track__isnull=False).select_related('track')
    playlists_count = Playlist.objects.filter(user=request.user).count()
    
    context = {
        'profile': profile,
        'followed_releases': followed_releases,
        'trending': trending,
        'liked_releases': liked_releases,
        'liked_tracks': liked_tracks,
        'following_count': followed_artists.count(),
        'playlists_count': playlists_count,
    }
    
    return render(request, "fan/fanboard.html", context)

@login_required(login_url='login')
def fan_library(request):
    """Fan's music library - liked songs and releases"""
    try:
        profile = UserProfile.objects.get(user=request.user)
        if profile.role != 'Fan':
            messages.error(request, "Only fans can access this page.")
            return redirect('artistboard')
    except UserProfile.DoesNotExist:
        messages.error(request, "Please create a profile first.")
        return redirect('choose-profile')
    
    # Get liked releases
    liked_releases = Like.objects.filter(
        user=request.user,
        release__isnull=False
    ).select_related('release').order_by('-created_at')
    
    # Get liked tracks
    liked_tracks = Like.objects.filter(
        user=request.user,
        track__isnull=False
    ).select_related('track', 'track__release').order_by('-created_at')
    
    # Get followed artists
    followed_artists = Follow.objects.filter(
        follower=request.user
    ).select_related('following')
    
    context = {
        'profile': profile,
        'liked_releases': liked_releases,
        'liked_tracks': liked_tracks,
        'followed_artists': followed_artists,
        'total_likes': liked_releases.count() + liked_tracks.count(),
        'total_following': followed_artists.count(),
    }
    
    return render(request, "fan/library.html", context)


@login_required(login_url='login')
def fan_playlist(request, playlist_id=None):
    """Manage playlists - create, view, edit, delete"""
    try:
        profile = UserProfile.objects.get(user=request.user)
        if profile.role != 'Fan':
            messages.error(request, "Only fans can access this page.")
            return redirect('artistboard')
    except UserProfile.DoesNotExist:
        messages.error(request, "Please create a profile first.")
        return redirect('choose-profile')
    
    # Get all user's playlists
    playlists = Playlist.objects.filter(user=request.user).order_by('-created_at')
    
    # Handle create playlist
    if request.method == "POST" and request.POST.get('action') == 'create':
        name = request.POST.get('name')
        is_public = request.POST.get('is_public') == 'on'
        
        if not name:
            messages.error(request, "Playlist name is required.")
            return redirect('fan_playlist')
        
        if Playlist.objects.filter(user=request.user, name=name).exists():
            messages.error(request, "You already have a playlist with this name.")
            return redirect('fan_playlist')
        
        playlist = Playlist.objects.create(
            user=request.user,
            name=name,
            is_public=is_public
        )
        messages.success(request, f"Playlist '{name}' created successfully!")
        return redirect('fan_playlist_detail', playlist_id=playlist.id)
    
    # Handle edit/delete playlist
    if playlist_id:
        playlist = get_object_or_404(Playlist, id=playlist_id, user=request.user)
        
        if request.method == "POST":
            action = request.POST.get('action')
            
            if action == 'update':
                playlist.name = request.POST.get('name', playlist.name)
                playlist.is_public = request.POST.get('is_public') == 'on'
                playlist.save()
                messages.success(request, "Playlist updated successfully!")
                return redirect('fan_playlist_detail', playlist_id=playlist.id)
            
            elif action == 'add_release':
                release_id = request.POST.get('release_id')
                release = get_object_or_404(Release, id=release_id, status='published')
                if release not in playlist.releases.all():
                    playlist.releases.add(release)
                    messages.success(request, f"Added '{release.title}' to playlist!")
                else:
                    messages.info(request, "Release already in playlist.")
                return redirect('fan_playlist_detail', playlist_id=playlist.id)
            
            elif action == 'remove_release':
                release_id = request.POST.get('release_id')
                release = get_object_or_404(Release, id=release_id)
                playlist.releases.remove(release)
                messages.success(request, f"Removed '{release.title}' from playlist.")
                return redirect('fan_playlist_detail', playlist_id=playlist.id)
            
            elif action == 'delete':
                playlist.delete()
                messages.success(request, "Playlist deleted successfully!")
                return redirect('fan_playlist')
        
        # Get releases not already in playlist
        available_releases = Release.objects.filter(
            status='published',
            is_public=True
        ).exclude(id__in=playlist.releases.all())
        
        return render(request, "fan/playlist_detail.html", {
            'profile': profile,
            'playlist': playlist,
            'playlists': playlists,
            'available_releases': available_releases,
        })
    
    return render(request, "fan/playlists.html", {
        'profile': profile,
        'playlists': playlists,
    })

@login_required(login_url='login')
@fan_required
def fan_search(request):
    """Search for artists, releases, and tracks"""
    query = request.GET.get('q', '')
    search_type = request.GET.get('type', 'all')
    
    artists = []
    releases = []
    tracks = []
    
    if query:
        if search_type in ['all', 'artists']:
            artists = User.objects.filter(
                Q(username__icontains=query) |
                Q(fullname__icontains=query) |
                Q(userprofile__artist_name__icontains=query)
            ).filter(userprofile__role='Artist')
        
        if search_type in ['all', 'releases']:
            releases = Release.objects.filter(
                Q(title__icontains=query) |
                Q(artist__username__icontains=query) |
                Q(genre__icontains=query)
            ).filter(status='published', is_public=True)
        
        if search_type in ['all', 'tracks']:
            tracks = Track.objects.filter(
                Q(title__icontains=query)
            ).filter(release__status='published', release__is_public=True)
    
    context = {
        'query': query,
        'search_type': search_type,
        'artists': artists,
        'releases': releases,
        'tracks': tracks,
        'total_results': len(artists) + len(releases) + len(tracks),
    }
    
    return render(request, "fan/search.html", context)

@login_required(login_url='login')
@artist_required
def artistboard(request):
    """Artist dashboard - only accessible by users with Artist role"""
    # Check if user has a profile
    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        messages.error(request, "Please create a profile first.")
        return redirect('choose-profile')
    
    # Check if user has the Artist role
    if profile.role != 'Artist':
        messages.error(request, "Access denied. Only artists can access this page.")
        # Redirect based on their actual role
        if profile.role == 'Fan':
            return redirect('fanboard')
        else:
            return redirect('index')
    
    # Get artist's releases
    releases = Release.objects.filter(artist=request.user).order_by('-created_at')
    
    return render(request, "auth/artistboard.html", {
        'profile': profile,
        'releases': releases,
        'total_releases': releases.count(),
        'published': releases.filter(status='published').count(),
        'pending': releases.filter(status='pending').count(),
        'drafts': releases.filter(status='draft').count(),
        'rejected': releases.filter(status='rejected').count(),
    })
    
    
#Artists create releases
@login_required(login_url='login')
@artist_required
def create_release(request):
    # Check if user has an artist profile
    try:
        profile = UserProfile.objects.get(user=request.user)
        if profile.role != 'Artist':
            messages.error(request, "Only artists can create releases.")
            return redirect('fanboard')
    except UserProfile.DoesNotExist:
        messages.error(request, "Please create a profile first.")
        return redirect('choose-profile')
    
    if request.method == "POST":
        # Get basic release information
        title = request.POST.get('title')
        release_type = request.POST.get('release_type')
        genre = request.POST.get('genre')
        description = request.POST.get('description')
        release_date = request.POST.get('release_date')
        is_free = request.POST.get('is_free') == 'on'
        price = request.POST.get('price', 0.00)
        tags = request.POST.get('tags')
        language = request.POST.get('language')
        is_public = request.POST.get('is_public') == 'on'
        
        # Validation
        if not title:
            messages.error(request, "Title is required.")
            return redirect('create_release')
        
        if not release_type:
            messages.error(request, "Release type is required.")
            return redirect('create_release')
        
        # Create the release
        try:
            release = Release.objects.create(
                title=title,
                artist=request.user,
                artist_profile=profile,
                release_type=release_type,
                genre=genre,
                description=description,
                release_date=release_date or timezone.now().date(),
                is_free=is_free,
                price=price if not is_free else 0.00,
                tags=tags,
                language=language,
                is_public=is_public,
                status='draft',
                track_count=0,
            )
            
            messages.success(request, f"Release '{title}' created successfully! Now add tracks.")
            
            # Redirect to add tracks page
            return redirect('add_tracks', release_id=release.id)
            
        except Exception as e:
            messages.error(request, f"Error creating release: {str(e)}")
            return redirect('create_release')
    
    # GET request - show the form
    return render(request, "releases/create_release.html", {
        'release_types': Release.RELEASE_TYPES,
        'artist_profile': profile,
    })
   
@login_required(login_url='login')
def publish_release(request, release_id):
    release = get_object_or_404(Release, id=release_id, artist=request.user)
    
    if release.artist != request.user:
        messages.error(request, "You don't have permission to publish this release.")
        return redirect('artistboard')
    
    # Handle cover art upload directly from publish page
    if request.method == "POST" and request.FILES.get('cover_art'):
        cover_art = request.FILES['cover_art']
        
        if cover_art.size > 5 * 1024 * 1024:
            messages.error(request, "Cover art file is too large. Maximum size is 5MB.")
            return redirect('publish_release', release_id=release_id)
        
        if not cover_art.content_type.startswith('image/'):
            messages.error(request, "Please upload a valid image file (JPG, PNG, or GIF).")
            return redirect('publish_release', release_id=release_id)
        
        release.cover_art = cover_art
        release.save()
        
        messages.success(request, f"✅ Cover art uploaded successfully!")
        return redirect('publish_release', release_id=release_id)
    
    if request.method == "POST":
        action = request.POST.get('action')
        
        if action == 'publish':
            # Check if release has tracks
            if release.tracks.count() == 0:
                messages.error(request, "Cannot publish a release without tracks. Please add at least one track.")
                return redirect('add_tracks', release_id=release_id)
            
            # Check if cover art is uploaded
            if not release.cover_art:
                messages.error(request, "Please upload cover art before publishing.")
                return redirect('publish_release', release_id=release_id)
            
            # Check if all tracks have audio files
            tracks_without_audio = release.tracks.filter(audio_file__isnull=True)
            if tracks_without_audio.exists():
                messages.error(request, f"Please upload audio files for the following tracks: {', '.join([t.title for t in tracks_without_audio])}")
                return redirect('add_tracks', release_id=release_id)
            
            # Submit for review
            release.status = 'pending'
            release.is_public = False
            release.save()
            
            # Send notification to admins
            try:
                from django.core.mail import EmailMultiAlternatives
                from django.contrib.sites.shortcuts import get_current_site
                from django.template.loader import render_to_string
                
                current_site = get_current_site(request)
                admin_approval_link = f"http://{current_site.domain}/bayaplus/staff/review/{release.id}/"
                
                subject = f"🎵 New Release Pending Approval: {release.title}"
                
                # Admin email addresses - Update these!
                admin_emails = [
                    'edutrackplus12@gmail.com',  # Replace with actual admin emails
                    # 'admin2@example.com',
                ]
                
                # Plain text version
                text_content = f"""
                New Release Notification - BayaPlus Admin
                
                A new release has been submitted for review.
                
                Release Details:
                -----------------
                Title: {release.title}
                Artist: {release.artist_profile.artist_name or release.artist.username}
                Type: {release.get_release_type_display()}
                Genre: {release.genre or 'Not specified'}
                Tracks: {release.tracks.count()}
                Release Date: {release.release_date}
                Price: {'Free' if release.is_free else f'${release.price}'}
                Cover Art: {'✅ Yes' if release.cover_art else '❌ No'}
                Audio Files: {'✅ Yes' if release.tracks.filter(audio_file__isnull=False).exists() else '❌ No'}
                
                Review Link: {admin_approval_link}
                
                This is an automated notification from BayaPlus.
                """
                
                # HTML version
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333; }}
                        .header {{ background: linear-gradient(135deg, #dc2626, #fbbf24); color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }}
                        .content {{ padding: 30px; background: #f9f9f9; border-radius: 0 0 10px 10px; }}
                        .details {{ background: white; padding: 20px; border-radius: 5px; margin: 15px 0; }}
                        .detail-row {{ display: flex; padding: 8px 0; border-bottom: 1px solid #eee; }}
                        .detail-row:last-child {{ border-bottom: none; }}
                        .label {{ font-weight: bold; color: #555; width: 120px; }}
                        .value {{ color: #333; }}
                        .btn {{ display: inline-block; padding: 12px 30px; background: #fbbf24; color: black; text-decoration: none; border-radius: 5px; font-weight: bold; }}
                        .btn:hover {{ background: #f59e0b; }}
                        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
                        .status-badge {{ display: inline-block; padding: 3px 12px; background: #ff9800; color: white; border-radius: 20px; font-size: 12px; }}
                    </style>
                </head>
                <body>
                    <div class="header">
                        <h1>🎵 BayaPlus</h1>
                    </div>
                    <div class="content">
                        <h2>📢 New Release Pending Approval</h2>
                        <p>A new release has been submitted for review.</p>
                        
                        <div class="details">
                            <h3>Release Details</h3>
                            <div class="detail-row">
                                <span class="label">Title:</span>
                                <span class="value"><strong>{release.title}</strong></span>
                            </div>
                            <div class="detail-row">
                                <span class="label">Artist:</span>
                                <span class="value">{release.artist_profile.artist_name or release.artist.username}</span>
                            </div>
                            <div class="detail-row">
                                <span class="label">Type:</span>
                                <span class="value">{release.get_release_type_display()}</span>
                            </div>
                            <div class="detail-row">
                                <span class="label">Genre:</span>
                                <span class="value">{release.genre or 'Not specified'}</span>
                            </div>
                            <div class="detail-row">
                                <span class="label">Tracks:</span>
                                <span class="value">{release.tracks.count()}</span>
                            </div>
                            <div class="detail-row">
                                <span class="label">Cover Art:</span>
                                <span class="value">{'✅ Yes' if release.cover_art else '❌ No'}</span>
                            </div>
                            <div class="detail-row">
                                <span class="label">Audio Files:</span>
                                <span class="value">{'✅ Yes' if release.tracks.filter(audio_file__isnull=False).exists() else '❌ No'}</span>
                            </div>
                            <div class="detail-row">
                                <span class="label">Status:</span>
                                <span class="value"><span class="status-badge">Pending Review</span></span>
                            </div>
                        </div>
                        
                        <p style="text-align: center;">
                            <a href="{admin_approval_link}" class="btn">📋 Review Release</a>
                        </p>
                        <p style="text-align: center; font-size: 12px; color: #999;">
                            Or copy this link: {admin_approval_link}
                        </p>
                    </div>
                    <div class="footer">
                        <p>&copy; 2026 BayaPlus. All rights reserved.</p>
                        <p>This is an automated notification.</p>
                    </div>
                </body>
                </html>
                """
                
                # Send email to all admins
                for admin_email in admin_emails:
                    try:
                        msg = EmailMultiAlternatives(
                            subject,
                            text_content,
                            'BayaPlus Admin <noreply@bayaplus.com>',
                            [admin_email]
                        )
                        msg.attach_alternative(html_content, "text/html")
                        msg.send()
                        print(f"✅ Admin notification sent to {admin_email}")
                    except Exception as e:
                        print(f"❌ Failed to send to {admin_email}: {str(e)}")
                
                messages.success(request, f"✅ Release '{release.title}' submitted for admin review! Admin emails have been sent.")
                
            except Exception as e:
                print(f"❌ Error sending admin notifications: {str(e)}")
                messages.warning(request, f"Release submitted but admin notifications failed: {str(e)}")
            
            return redirect('artistboard')
            
        elif action == 'save_draft':
            release.status = 'draft'
            release.save()
            messages.success(request, f"Release '{release.title}' saved as draft.")
            return redirect('artistboard')
            
        elif action == 'delete':
            release.delete()
            messages.success(request, f"Release '{release.title}' has been deleted.")
            return redirect('artistboard')
    
    tracks = release.tracks.all().order_by('track_number')
    tracks_without_audio = release.tracks.filter(audio_file__isnull=True)
    
    return render(request, "releases/publish_release.html", {
        'release': release,
        'tracks': tracks,
        'track_count': tracks.count(),
        'tracks_without_audio': tracks_without_audio,
    }) 
    
@staff_member_required(login_url='login')
def admin_pending_releases(request):
    """Admin view to see all pending releases"""
    pending_releases = Release.objects.filter(status='pending').order_by('-created_at')
    all_releases = Release.objects.all()
    
    return render(request, "admin/pending_releases.html", {
        'pending_releases': pending_releases,
        'pending_count': pending_releases.count(),
        'published_count': all_releases.filter(status='published').count(),
        'rejected_count': all_releases.filter(status='rejected').count(),
        'draft_count': all_releases.filter(status='draft').count(),
    })

@staff_member_required(login_url='login')
def admin_review_release(request, release_id):
    """Admin view to review and approve/reject releases with audio playback"""
    release = get_object_or_404(Release, id=release_id)
    
    if request.method == "POST":
        action = request.POST.get('action')
        admin_notes = request.POST.get('admin_notes', '')
        
        if action == 'approve':
            release.status = 'published'
            release.is_public = True
            release.save()
            
            # Send approval notification to artist
            send_artist_approval_notification(request, release)
            
            messages.success(request, f"Release '{release.title}' has been approved and published!")
            
        elif action == 'reject':
            release.status = 'rejected'
            release.save()
            
            # Send rejection notification to artist
            send_artist_rejection_notification(request, release, admin_notes)
            
            messages.success(request, f"Release '{release.title}' has been rejected.")
            
        elif action == 'request_changes':
            release.status = 'draft'
            release.save()
            
            # Send revision request to artist
            send_artist_revision_request(request, release, admin_notes)
            
            messages.info(request, f"Revision request sent to artist for '{release.title}'.")
        
        return redirect('admin_pending_releases')
    
    tracks = release.tracks.all().order_by('track_number')
    
    # Prepare track data for audio player
    track_data = []
    for track in tracks:
        track_data.append({
            'id': track.id,
            'title': track.title,
            'track_number': track.track_number,
            'duration': track.duration or '--',
            'audio_url': track.audio_file.url if track.audio_file else None,
            'is_explicit': track.is_explicit,
        })
    
    return render(request, "admin/review_release.html", {
        'release': release,
        'tracks': tracks,
        'track_data': track_data,
        'track_count': tracks.count(),
        'has_audio': tracks.filter(audio_file__isnull=False).exists(),
    })

def send_artist_approval_notification(request, release):
    """Send approval notification to the artist"""
    subject = f"Release Approved: {release.title}"
    
    # Plain text
    text_content = f"""
    Congratulations {release.artist_profile.artist_name or release.artist.username}!
    
    Your release "{release.title}" has been approved and is now live on BayaPlus!
    
    View your release: http://{get_current_site(request).domain}/bayaplus/release/{release.id}/
    
    Keep creating amazing music!
    
    - BayaPlus Team
    """
    
    # HTML
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #4CAF50; color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ padding: 30px; background: #f9f9f9; border-radius: 0 0 10px 10px; }}
            .btn {{ display: inline-block; padding: 12px 30px; background: #4CAF50; color: white; text-decoration: none; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎵 Release Approved!</h1>
        </div>
        <div class="content">
            <h2>Congratulations {release.artist_profile.artist_name or release.artist.username}!</h2>
            <p>Your release <strong>"{release.title}"</strong> has been approved and is now live on BayaPlus!</p>
            <p style="text-align: center;">
                <a href="http://{get_current_site(request).domain}/bayaplus/release/{release.id}/" class="btn">View Your Release</a>
            </p>
            <p>Keep creating amazing music!</p>
            <p>- BayaPlus Team</p>
        </div>
    </body>
    </html>
    """
    
    try:
        msg = EmailMultiAlternatives(subject, text_content, settings.ADMIN_NOTIFICATION_EMAIL, [release.artist.email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
    except Exception as e:
        print(f"Error sending approval notification: {str(e)}")

def send_artist_rejection_notification(request, release, admin_notes):
    """Send rejection notification to the artist"""
    subject = f"Release Update: {release.title}"
    
    text_content = f"""
    Hi {release.artist_profile.artist_name or release.artist.username},
    
    Your release "{release.title}" was not approved for publication.
    
    Reason: {admin_notes or 'No specific reason provided'}
    
    Please make the necessary changes and resubmit.
    
    - BayaPlus Team
    """
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #f44336; color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ padding: 30px; background: #f9f9f9; border-radius: 0 0 10px 10px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Release Update</h1>
        </div>
        <div class="content">
            <h2>Hi {release.artist_profile.artist_name or release.artist.username},</h2>
            <p>Your release <strong>"{release.title}"</strong> was not approved for publication.</p>
            <p><strong>Reason:</strong> {admin_notes or 'No specific reason provided'}</p>
            <p>Please make the necessary changes and resubmit.</p>
            <p>- BayaPlus Team</p>
        </div>
    </body>
    </html>
    """
    
    try:
        msg = EmailMultiAlternatives(subject, text_content, settings.ADMIN_NOTIFICATION_EMAIL, [release.artist.email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
    except Exception as e:
        print(f"Error sending rejection notification: {str(e)}")

def send_artist_revision_request(request, release, admin_notes):
    """Send revision request to the artist"""
    subject = f"Revision Requested: {release.title}"
    
    text_content = f"""
    Hi {release.artist_profile.artist_name or release.artist.username},
    
    Your release "{release.title}" needs some revisions before it can be approved.
    
    Feedback: {admin_notes or 'Please review and make the necessary changes.'}
    
    You can edit your release here: http://{get_current_site(request).domain}/bayaplus/edit-release/{release.id}/
    
    - BayaPlus Team
    """
    
    try:
        send_mail(
            subject,
            text_content,
            settings.ADMIN_NOTIFICATION_EMAIL,
            [release.artist.email],
            fail_silently=False,
        )
    except Exception as e:
        print(f"Error sending revision request: {str(e)}")
        

@login_required(login_url='login')
def add_tracks(request, release_id):
    # Get the release
    release = get_object_or_404(Release, id=release_id, artist=request.user)
    
    # Check if user owns this release
    if release.artist != request.user:
        messages.error(request, "You don't have permission to edit this release.")
        return redirect('artistboard')
    
    if request.method == "POST":
        track_title = request.POST.get('track_title')
        track_number = request.POST.get('track_number')
        duration_str = request.POST.get('duration')
        is_explicit = request.POST.get('is_explicit') == 'on'
        audio_file = request.FILES.get('audio_file')  # Get the uploaded audio file
        
        if not track_title:
            messages.error(request, "Track title is required.")
            return redirect('add_tracks', release_id=release_id)
        
        if not audio_file:
            messages.error(request, "Audio file is required for each track.")
            return redirect('add_tracks', release_id=release_id)
        
        # Validate audio file size (max 50MB)
        if audio_file.size > 50 * 1024 * 1024:
            messages.error(request, f"Audio file '{audio_file.name}' is too large. Maximum size is 50MB.")
            return redirect('add_tracks', release_id=release_id)
        
        # Validate audio file type
        allowed_types = ['audio/mpeg', 'audio/wav', 'audio/flac', 'audio/mp3', 'audio/mp4', 'audio/x-m4a']
        if audio_file.content_type not in allowed_types:
            messages.error(request, f"Please upload a valid audio file (MP3, WAV, or FLAC).")
            return redirect('add_tracks', release_id=release_id)
        
        try:
            # Create the track with audio file
            track = Track.objects.create(
                release=release,
                title=track_title,
                track_number=track_number or release.tracks.count() + 1,
                duration=duration_str,
                is_explicit=is_explicit,
                audio_file=audio_file,  # Save the audio file
            )
            
            # Update track count on release
            release.track_count = release.tracks.count()
            release.save()
            
            messages.success(request, f"✅ Track '{track_title}' added with audio file '{audio_file.name}'!")
            
            # Check if user wants to add another track
            if request.POST.get('add_another') == 'on' or not request.POST.get('finish'):
                return redirect('add_tracks', release_id=release_id)
            else:
                return redirect('publish_release', release_id=release_id)
                
        except Exception as e:
            messages.error(request, f"Error adding track: {str(e)}")
            return redirect('add_tracks', release_id=release_id)
    
    # GET request - show the form
    tracks = release.tracks.all().order_by('track_number')
    return render(request, "releases/add_tracks.html", {
        'release': release,
        'tracks': tracks,
        'track_count': tracks.count(),
    })
    
    
@login_required(login_url='login')
def upload_cover_art(request, release_id):
    """Upload cover art for a release (3000x3000 recommended)"""
    release = get_object_or_404(Release, id=release_id, artist=request.user)
    
    if release.artist != request.user:
        messages.error(request, "You don't have permission to edit this release.")
        return redirect('artistboard')
    
    if request.method == "POST" and request.FILES.get('cover_art'):
        cover_art = request.FILES['cover_art']
        
        # Validate file size (max 5MB)
        if cover_art.size > 5 * 1024 * 1024:
            messages.error(request, "Cover art file is too large. Maximum size is 5MB.")
            return redirect('add_tracks', release_id=release_id)
        
        # Validate file type
        if not cover_art.content_type.startswith('image/'):
            messages.error(request, "Please upload a valid image file (JPG, PNG, or GIF).")
            return redirect('add_tracks', release_id=release_id)
        
        # Validate dimensions (optional - you can check image size)
        try:
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(cover_art.read()))
            width, height = img.size
            
            if width != height:
                messages.warning(request, f"Image is {width}x{height}. Recommended: 3000x3000 (square).")
                # Allow it but warn
            
            if width < 500 or height < 500:
                messages.warning(request, f"Image is {width}x{height}. Recommended: 3000x3000 for best quality.")
            
            # Reset file pointer
            cover_art.seek(0)
            
        except:
            # If PIL is not installed or can't read image
            pass
        
        release.cover_art = cover_art
        release.save()
        
        messages.success(request, f"✅ Cover art uploaded successfully!")
    
    return redirect('add_tracks', release_id=release_id)

def parse_duration(duration_str):
    """
    Parse duration string to timedelta object.
    Supports formats:
    - "3:45" (minutes:seconds)
    - "1:30:45" (hours:minutes:seconds)
    - "120" (seconds)
    - "2m 30s" (minutes and seconds)
    """
    if not duration_str:
        return None
    
    duration_str = duration_str.strip()
    
    # Try to parse HH:MM:SS or MM:SS
    if ':' in duration_str:
        parts = duration_str.split(':')
        if len(parts) == 2:
            # MM:SS
            minutes = int(parts[0])
            seconds = int(parts[1])
            return timedelta(minutes=minutes, seconds=seconds)
        elif len(parts) == 3:
            # HH:MM:SS
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2])
            return timedelta(hours=hours, minutes=minutes, seconds=seconds)
    
    # Try to parse "2m 30s" format
    import re
    minutes = 0
    seconds = 0
    
    minute_match = re.search(r'(\d+)\s*m', duration_str)
    if minute_match:
        minutes = int(minute_match.group(1))
    
    second_match = re.search(r'(\d+)\s*s', duration_str)
    if second_match:
        seconds = int(second_match.group(1))
    
    if minutes > 0 or seconds > 0:
        return timedelta(minutes=minutes, seconds=seconds)
    
    # Try to parse as plain seconds
    try:
        total_seconds = int(duration_str)
        return timedelta(seconds=total_seconds)
    except ValueError:
        pass
    
    # If all else fails, return None
    return None
    # Get the release
    release = get_object_or_404(Release, id=release_id, artist=request.user)
    
    # Check if user owns this release
    if release.artist != request.user:
        messages.error(request, "You don't have permission to edit this release.")
        return redirect('artistboard')
    
    if request.method == "POST":
        track_title = request.POST.get('track_title')
        track_number = request.POST.get('track_number')
        duration = request.POST.get('duration')
        is_explicit = request.POST.get('is_explicit') == 'on'
        
        if not track_title:
            messages.error(request, "Track title is required.")
            return redirect('add_tracks', release_id=release_id)
        
        try:
            # Create the track
            track = Track.objects.create(
                release=release,
                title=track_title,
                track_number=track_number or release.tracks.count() + 1,
                duration=duration,
                is_explicit=is_explicit,
            )
            
            # Update track count on release
            release.track_count = release.tracks.count()
            release.save()
            
            messages.success(request, f"Track '{track_title}' added successfully!")
            
            # Check if user wants to add another track
            if request.POST.get('add_another') == 'on':
                return redirect('add_tracks', release_id=release_id)
            else:
                return redirect('publish_release', release_id=release_id)
                
        except Exception as e:
            messages.error(request, f"Error adding track: {str(e)}")
            return redirect('add_tracks', release_id=release_id)
    
    # GET request - show the form
    tracks = release.tracks.all().order_by('track_number')
    return render(request, "releases/add_tracks.html", {
        'release': release,
        'tracks': tracks,
        'track_count': tracks.count(),
    })
    
    
@login_required(login_url='login')
def delete_track(request, release_id, track_id):
    """Delete a track from a release"""
    release = get_object_or_404(Release, id=release_id, artist=request.user)
    track = get_object_or_404(Track, id=track_id, release=release)
    
    if request.method == "POST":
        track_title = track.title
        track.delete()
        
        # Update track count
        release.track_count = release.tracks.count()
        release.save()
        
        messages.success(request, f"Track '{track_title}' deleted successfully.")
        return redirect('add_tracks', release_id=release_id)
    
    # If GET request, redirect back
    return redirect('add_tracks', release_id=release_id)

@login_required(login_url='login')
def delete_release(request, release_id):
    """Delete a release"""
    release = get_object_or_404(Release, id=release_id, artist=request.user)
    
    if request.method == "POST":
        release_title = release.title
        release.delete()
        messages.success(request, f"Release '{release_title}' deleted successfully.")
        return redirect('artistboard')
    
    return redirect('artistboard')

@login_required(login_url='login')
def edit_release(request, release_id):
    """Edit an existing release"""
    release = get_object_or_404(Release, id=release_id, artist=request.user)
    
    if release.artist != request.user:
        messages.error(request, "You don't have permission to edit this release.")
        return redirect('artistboard')
    
    if release.status == 'published':
        messages.warning(request, "This release is published. Editing will save it as a draft.")
    
    if request.method == "POST":
        # Update release information
        release.title = request.POST.get('title', release.title)
        release.release_type = request.POST.get('release_type', release.release_type)
        release.genre = request.POST.get('genre', release.genre)
        release.description = request.POST.get('description', release.description)
        release.release_date = request.POST.get('release_date', release.release_date)
        release.is_free = request.POST.get('is_free') == 'on'
        release.price = request.POST.get('price', 0.00) if not release.is_free else 0.00
        release.tags = request.POST.get('tags', release.tags)
        release.language = request.POST.get('language', release.language)
        release.is_public = request.POST.get('is_public') == 'on'
        
        # If published, change to draft
        if release.status == 'published':
            release.status = 'draft'
        
        release.save()
        
        messages.success(request, f"Release '{release.title}' updated successfully!")
        return redirect('publish_release', release_id=release.id)
    
    return render(request, "releases/edit_release.html", {
        'release': release,
        'release_types': Release.RELEASE_TYPES,
    })
    
def release_detail(request, release_id):
    """View a single release detail"""
    release = get_object_or_404(Release, id=release_id, status='published', is_public=True)
    
    # Get tracks
    tracks = release.tracks.all().order_by('track_number')
    
    # Get comments
    comments = release.comments.filter(is_approved=True)[:10]
    
    # Check if user liked this release
    user_liked = False
    if request.user.is_authenticated:
        from .models import Like
        user_liked = Like.objects.filter(user=request.user, release=release).exists()
    
    return render(request, "releases/release_detail.html", {
        'release': release,
        'tracks': tracks,
        'comments': comments,
        'user_liked': user_liked,
        'total_likes': release.total_likes,
    })
    
def all_releases(request):
    """View all public releases (browse page)"""
    releases = Release.objects.filter(
        status='published', 
        is_public=True
    ).order_by('-release_date')
    
    # Filter by release type
    release_type = request.GET.get('type')
    if release_type:
        releases = releases.filter(release_type=release_type)
    
    # Search
    search_query = request.GET.get('q')
    if search_query:
        releases = releases.filter(
            Q(title__icontains=search_query) |
            Q(artist__username__icontains=search_query) |
            Q(genre__icontains=search_query) |
            Q(artist_profile__artist_name__icontains=search_query)
        )
    
    # Get trending releases (by plays/likes)
    trending_releases = Release.objects.filter(
        status='published', 
        is_public=True
    ).order_by('-total_plays', '-total_likes')[:10]
    
    # Get recent releases
    recent_releases = Release.objects.filter(
        status='published', 
        is_public=True
    ).order_by('-created_at')[:10]
    
    # Get all release types for filter
    release_types = Release.RELEASE_TYPES
    
    context = {
        'releases': releases,
        'release_types': release_types,
        'current_type': release_type,
        'search_query': search_query,
        'total_releases': releases.count(),
        'trending_releases': trending_releases,
        'recent_releases': recent_releases,
    }
    
    return render(request, "releases/all_releases.html", context) 
    
@login_required(login_url='login')
def my_releases(request):
    """View all releases by the logged-in artist"""
    try:
        profile = UserProfile.objects.get(user=request.user)
        if profile.role != 'Artist':
            messages.error(request, "Only artists can access this page.")
            return redirect('fanboard')
    except UserProfile.DoesNotExist:
        messages.error(request, "Please create a profile first.")
        return redirect('choose-profile')
    
    releases = Release.objects.filter(artist=request.user).order_by('-created_at')
    
    return render(request, "releases/my_releases.html", {
        'releases': releases,
        'profile': profile,
        'total_releases': releases.count(),
        'published': releases.filter(status='published').count(),
        'pending': releases.filter(status='pending').count(),
        'drafts': releases.filter(status='draft').count(),
        'rejected': releases.filter(status='rejected').count(),
    })
    
@login_required(login_url='login')
def my_drafts(request):
    """View draft releases"""
    try:
        profile = UserProfile.objects.get(user=request.user)
        if profile.role != 'Artist':
            messages.error(request, "Only artists can access this page.")
            return redirect('fanboard')
    except UserProfile.DoesNotExist:
        messages.error(request, "Please create a profile first.")
        return redirect('choose-profile')
    
    releases = Release.objects.filter(artist=request.user, status='draft').order_by('-updated_at')
    
    return render(request, "releases/my_drafts.html", {
        'releases': releases,
        'profile': profile,
    })

@login_required(login_url='login')
def my_pending_releases(request):
    """View pending releases waiting for admin review"""
    try:
        profile = UserProfile.objects.get(user=request.user)
        if profile.role != 'Artist':
            messages.error(request, "Only artists can access this page.")
            return redirect('fanboard')
    except UserProfile.DoesNotExist:
        messages.error(request, "Please create a profile first.")
        return redirect('choose-profile')
    
    releases = Release.objects.filter(artist=request.user, status='pending').order_by('-created_at')
    
    return render(request, "releases/my_pending.html", {
        'releases': releases,
        'profile': profile,
    })
    
    
def artist_releases(request, username):
    """View all public releases by a specific artist"""
    artist = get_object_or_404(User, username=username)
    
    # Check if artist has a profile
    try:
        profile = UserProfile.objects.get(user=artist)
    except UserProfile.DoesNotExist:
        profile = None
    
    # Get published releases
    releases = Release.objects.filter(
        artist=artist,
        status='published',
        is_public=True
    ).order_by('-release_date')
    
    # Count total likes for follower count
    total_likes = sum(release.total_likes for release in releases)
    
    # Check if current user follows this artist
    is_following = False
    if request.user.is_authenticated:
        is_following = Follow.objects.filter(
            follower=request.user,
            following=artist
        ).exists()
    
    return render(request, "releases/artist_releases.html", {
        'artist': artist,
        'profile': profile,
        'releases': releases,
        'total_releases': releases.count(),
        'followers_count': total_likes,  # Using likes as follower count
        'is_following': is_following,
    })
 
@login_required(login_url='login')
def like_release(request, release_id):
    """Like or unlike a release"""
    release = get_object_or_404(Release, id=release_id)
    
    if request.method == "POST":
        # Check if already liked
        like, created = Like.objects.get_or_create(
            user=request.user,
            release=release
        )
        
        if not created:
            # Unlike
            like.delete()
            release.total_likes -= 1
            release.save()
            liked = False
            message = f"Unliked '{release.title}'"
        else:
            # Like
            release.total_likes += 1
            release.save()
            liked = True
            message = f"Liked '{release.title}'!"
        
        # Check if it's an AJAX request
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'liked': liked,
                'total_likes': release.total_likes,
                'message': message
            })
        
        messages.success(request, message)
        return redirect('release_detail', release_id=release_id)
    
    return redirect('release_detail', release_id=release_id)


@login_required(login_url='login')
def like_track(request, track_id):
    """Like or unlike a track"""
    track = get_object_or_404(Track, id=track_id)
    
    if request.method == "POST":
        like, created = Like.objects.get_or_create(
            user=request.user,
            track=track
        )
        
        if not created:
            like.delete()
            liked = False
            message = f"Unliked '{track.title}'"
        else:
            liked = True
            message = f"Liked '{track.title}'!"
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'liked': liked,
                'message': message
            })
        
        messages.success(request, message)
        return redirect('release_detail', release_id=track.release.id)
    
    return redirect('release_detail', release_id=track.release.id)

def release_detail(request, release_id):
    """View a single release detail"""
    release = get_object_or_404(Release, id=release_id, status='published', is_public=True)
    
    # Get tracks
    tracks = release.tracks.all().order_by('track_number')
    
    # Get comments
    comments = release.comments.filter(is_approved=True)[:10]
    
    # Check if user liked this release
    user_liked = False
    if request.user.is_authenticated:
        from .models import Like
        user_liked = Like.objects.filter(user=request.user, release=release).exists()
    
    return render(request, "releases/release_detail.html", {
        'release': release,
        'tracks': tracks,
        'comments': comments,
        'user_liked': user_liked,
        'total_likes': release.total_likes,
    })
    
@login_required(login_url='login')
def add_comment(request, release_id):
    """Add a comment to a release"""
    release = get_object_or_404(Release, id=release_id, status='published')
    
    if request.method == "POST":
        content = request.POST.get('content')
        parent_id = request.POST.get('parent_id')
        
        if not content or not content.strip():
            messages.error(request, "Comment cannot be empty.")
            return redirect('release_detail', release_id=release_id)
        
        try:
            comment = Comment.objects.create(
                user=request.user,
                release=release,
                content=content.strip(),
                parent_id=parent_id if parent_id else None,
            )
            
            # Update comment count
            release.total_comments = release.comments.filter(is_approved=True).count()
            release.save()
            
            messages.success(request, "Comment added successfully!")
        except Exception as e:
            messages.error(request, f"Error adding comment: {str(e)}")
    
    return redirect('release_detail', release_id=release_id)


@login_required(login_url='login')
def delete_comment(request, comment_id):
    """Delete a comment (owner or admin only)"""
    comment = get_object_or_404(Comment, id=comment_id)
    release_id = comment.release.id
    
    # Check if user is the comment owner or admin
    if request.user == comment.user or request.user.is_staff:
        comment.delete()
        
        # Update comment count
        release = Release.objects.get(id=release_id)
        release.total_comments = release.comments.filter(is_approved=True).count()
        release.save()
        
        messages.success(request, "Comment deleted successfully.")
    else:
        messages.error(request, "You don't have permission to delete this comment.")
    
    return redirect('release_detail', release_id=release_id)

@login_required(login_url='login')
def analytics(request):
    """Artist analytics dashboard"""
    # Check if user has an artist profile
    try:
        profile = UserProfile.objects.get(user=request.user)
        if profile.role != 'Artist':
            messages.error(request, "Only artists can access analytics.")
            return redirect('fanboard')
    except UserProfile.DoesNotExist:
        messages.error(request, "Please create a profile first.")
        return redirect('choose-profile')
    
    # Get artist's releases
    releases = Release.objects.filter(artist=request.user)
    
    # Basic Stats
    total_releases = releases.count()
    published_releases = releases.filter(status='published').count()
    total_plays = releases.aggregate(Sum('total_plays'))['total_plays__sum'] or 0
    total_likes = releases.aggregate(Sum('total_likes'))['total_likes__sum'] or 0
    total_comments = releases.aggregate(Sum('total_comments'))['total_comments__sum'] or 0
    
    # Top performing releases
    top_releases = releases.filter(status='published').order_by('-total_plays')[:5]
    
    # Engagement rate (likes + comments / plays)
    engagement_rate = 0
    if total_plays > 0:
        engagement_rate = round(((total_likes + total_comments) / total_plays) * 100, 2)
    
    # Monthly stats (last 6 months)
    six_months_ago = datetime.now().date() - timedelta(days=180)
    monthly_stats = []
    
    for i in range(6):
        month = datetime.now().date() - timedelta(days=30 * i)
        month_start = month.replace(day=1)
        if i == 0:
            month_end = datetime.now().date()
        else:
            next_month = month_start + timedelta(days=32)
            month_end = next_month.replace(day=1) - timedelta(days=1)
        
        month_releases = Release.objects.filter(
            artist=request.user,
            created_at__date__gte=month_start,
            created_at__date__lte=month_end
        )
        
        monthly_stats.append({
            'month': month.strftime('%b'),
            'releases': month_releases.count(),
            'plays': month_releases.aggregate(Sum('total_plays'))['total_plays__sum'] or 0,
            'likes': month_releases.aggregate(Sum('total_likes'))['total_likes__sum'] or 0,
        })
    
    monthly_stats.reverse()  # Show oldest to newest
    
    # Get release type distribution
    release_types = {}
    for release in releases:
        release_type = release.get_release_type_display()
        release_types[release_type] = release_types.get(release_type, 0) + 1
    
    # Get genre distribution
    genre_stats = {}
    for release in releases:
        if release.genre:
            genre_stats[release.genre] = genre_stats.get(release.genre, 0) + 1
    
    # Get top 10 tracks by plays
    top_tracks = Track.objects.filter(release__artist=request.user).order_by('-plays')[:10]
    
    # Calculate growth percentage
    current_month_total = monthly_stats[-1]['plays'] if monthly_stats else 0
    previous_month_total = monthly_stats[-2]['plays'] if len(monthly_stats) > 1 else 0
    growth_percentage = 0
    if previous_month_total > 0:
        growth_percentage = round(((current_month_total - previous_month_total) / previous_month_total) * 100, 1)
    
    context = {
        'profile': profile,
        'total_releases': total_releases,
        'published_releases': published_releases,
        'total_plays': total_plays,
        'total_likes': total_likes,
        'total_comments': total_comments,
        'engagement_rate': engagement_rate,
        'top_releases': top_releases,
        'monthly_stats': monthly_stats,
        'release_types': release_types,
        'genre_stats': genre_stats,
        'top_tracks': top_tracks,
        'growth_percentage': growth_percentage,
        'current_month_plays': current_month_total,
    }
    
    return render(request, "analytics/analytics.html", context)


@login_required(login_url='login')
def release_analytics(request, release_id):
    """Detailed analytics for a specific release"""
    release = get_object_or_404(Release, id=release_id, artist=request.user)
    
    # Basic stats for this release
    tracks = release.tracks.all()
    
    # Track analytics
    track_stats = []
    for track in tracks:
        track_stats.append({
            'title': track.title,
            'plays': track.plays,
            'duration': track.duration or '--',
        })
    
    # Daily plays for the last 30 days (you would need a Play model for this)
    # For now, we'll use placeholder data
    
    context = {
        'release': release,
        'tracks': tracks,
        'track_stats': track_stats,
        'total_tracks': tracks.count(),
        'total_plays': release.total_plays,
        'total_likes': release.total_likes,
        'total_comments': release.total_comments,
    }
    
    return render(request, "analytics/release_analytics.html", context)

@staff_member_required(login_url='login')
def admin_all_releases(request):
    """Admin view to see all releases"""
    releases = Release.objects.all().order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        releases = releases.filter(status=status_filter)
    
    # Search
    search_query = request.GET.get('q')
    if search_query:
        releases = releases.filter(
            Q(title__icontains=search_query) |
            Q(artist__username__icontains=search_query) |
            Q(artist_profile__artist_name__icontains=search_query)
        )
    
    return render(request, "admin/all_releases.html", {
        'releases': releases,
        'total': releases.count(),
        'published': releases.filter(status='published').count(),
        'pending': releases.filter(status='pending').count(),
        'drafts': releases.filter(status='draft').count(),
        'rejected': releases.filter(status='rejected').count(),
        'status_filter': status_filter,
        'search_query': search_query,
    })
    
@login_required(login_url='login')
def follow_artist(request, username):
    """Follow or unfollow an artist"""
    artist = get_object_or_404(User, username=username)
    
    # Prevent self-follow
    if request.user == artist:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': 'You cannot follow yourself.'
            })
        messages.error(request, "You cannot follow yourself.")
        return redirect('artist_releases', username=username)
    
    # Check if already following
    follow, created = Follow.objects.get_or_create(
        follower=request.user,
        following=artist
    )
    
    if not created:
        # Unfollow
        follow.delete()
        is_following = False
        message = f"Unfollowed {artist.username}"
    else:
        # Follow
        is_following = True
        message = f"Following {artist.username}"
    
    # Get updated follower count
    followers_count = Follow.objects.filter(following=artist).count()
    
    # Check if it's an AJAX request
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'is_following': is_following,
            'followers_count': followers_count,
            'message': message
        })
    
    messages.success(request, message)
    return redirect('artist_releases', username=username)

@login_required(login_url='login')
def following_list(request):
    """View all artists the user is following"""
    following = Follow.objects.filter(follower=request.user).select_related('following')
    
    return render(request, "social/following.html", {
        'following': following,
        'total_following': following.count(),
    })


@login_required(login_url='login')
def followers_list(request, username):
    """View all followers of an artist"""
    artist = get_object_or_404(User, username=username)
    followers = Follow.objects.filter(following=artist).select_related('follower')
    
    return render(request, "social/followers.html", {
        'artist': artist,
        'followers': followers,
        'total_followers': followers.count(),
    })
    
@login_required(login_url='login')
def profile_settings(request):
    """Profile settings - accessible by all authenticated users"""
    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        messages.error(request, "Please create a profile first.")
        return redirect('choose-profile')
    
    # Profile settings are accessible by both Artists and Fans
    # But show different options based on role
    is_artist = profile.role == 'Artist'
    
    if request.method == "POST":
        # ... existing code ...
        
        return render(request, "settings/profile_settings.html", {
            'profile': profile,
            'is_artist': is_artist,
        })
    
@staff_member_required(login_url='login')
def admin_dashboard(request):
    """Main admin dashboard with overview stats"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('index')
    
    # Admin doesn't need a UserProfile, but if they have one, use it
    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        profile = None
    
    # Statistics
    total_releases = Release.objects.count()
    total_artists = UserProfile.objects.filter(role='Artist').count()
    total_fans = UserProfile.objects.filter(role='Fan').count()
    total_users = User.objects.count()
    
    # Release stats
    pending_releases = Release.objects.filter(status='pending').count()
    published_releases = Release.objects.filter(status='published').count()
    rejected_releases = Release.objects.filter(status='rejected').count()
    draft_releases = Release.objects.filter(status='draft').count()
    
    # Recent releases
    recent_releases = Release.objects.all().order_by('-created_at')[:10]
    
    # Recent users
    recent_users = User.objects.all().order_by('-date_joined')[:5]
    
    # Pending releases for quick review
    pending_list = Release.objects.filter(status='pending').order_by('-created_at')[:5]
    
    context = {
        'profile': profile,
        'total_releases': total_releases,
        'total_artists': total_artists,
        'total_fans': total_fans,
        'total_users': total_users,
        'pending_releases': pending_releases,
        'published_releases': published_releases,
        'rejected_releases': rejected_releases,
        'draft_releases': draft_releases,
        'recent_releases': recent_releases,
        'recent_users': recent_users,
        'pending_list': pending_list,
    }
    
    return render(request, "admin/admin_dashboard.html", context)


@staff_member_required(login_url='login')
def admin_profile(request):
    """Admin profile management - only accessible by staff/admin users"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('index')
    
    # Admin might not have a UserProfile, handle gracefully
    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        profile = None
    
    if request.method == "POST":
        fullname = request.POST.get('fullname')
        email = request.POST.get('email')
        bio = request.POST.get('bio')
        
        # Update user
        user = request.user
        if fullname:
            user.fullname = fullname
        if email:
            user.email = email
        user.save()
        
        # Update or create profile (for admin avatar and bio)
        if profile:
            profile.bio = bio
            profile.save()
        else:
            # Create profile for admin without setting a role
            profile = UserProfile.objects.create(
                user=user,
                role='Artist',  # Default role, but admin won't use it
                bio=bio
            )
        
        # Handle avatar upload
        if request.FILES.get('avatar'):
            avatar = request.FILES['avatar']
            if avatar.size > 5 * 1024 * 1024:
                messages.error(request, "Avatar file is too large. Maximum size is 5MB.")
                return redirect('admin_profile')
            if not avatar.content_type.startswith('image/'):
                messages.error(request, "Please upload a valid image file.")
                return redirect('admin_profile')
            profile.avatar = avatar
            profile.save()
        
        messages.success(request, "Profile updated successfully!")
        return redirect('admin_profile')
    
    context = {
        'profile': profile,
        'user': request.user,
    }
    
    return render(request, "admin/admin_profile.html", context)


@staff_member_required(login_url='login')
def admin_all_users(request):
    """Admin view to manage all users"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('index')
    
    # Get all users with filters
    users = User.objects.all().order_by('-date_joined')
    
    # Filter by role (using UserProfile)
    role_filter = request.GET.get('role')
    if role_filter:
        if role_filter == 'artist':
            users = users.filter(userprofile__role='Artist')
        elif role_filter == 'fan':
            users = users.filter(userprofile__role='Fan')
        elif role_filter == 'admin':
            users = users.filter(is_staff=True)
    
    # Search
    search_query = request.GET.get('q')
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(fullname__icontains=search_query)
        )
    
    context = {
        'users': users,
        'total_users': users.count(),
        'role_filter': role_filter,
        'search_query': search_query,
    }
    
    return render(request, "admin/admin_users.html", context)


@staff_member_required(login_url='login')
def admin_user_detail(request, user_id):
    """Admin view to see user details and manage them"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('index')
    
    user_detail = get_object_or_404(User, id=user_id)
    
    # Get user profile
    try:
        profile = UserProfile.objects.get(user=user_detail)
    except UserProfile.DoesNotExist:
        profile = None
    
    # Get user's releases (if artist)
    releases = Release.objects.filter(artist=user_detail).order_by('-created_at')
    
    # Get user's followers (if artist)
    followers = Follow.objects.filter(following=user_detail).count() if profile and profile.role == 'Artist' else 0
    
    # Get user's following
    following = Follow.objects.filter(follower=user_detail).count()
    
    # Get user's likes
    likes = Like.objects.filter(user=user_detail).count()
    
    if request.method == "POST":
        action = request.POST.get('action')
        
        if action == 'toggle_active':
            user_detail.is_active = not user_detail.is_active
            user_detail.save()
            status = "activated" if user_detail.is_active else "deactivated"
            messages.success(request, f"User {user_detail.username} has been {status}.")
            
        elif action == 'toggle_staff':
            user_detail.is_staff = not user_detail.is_staff
            user_detail.save()
            status = "granted admin" if user_detail.is_staff else "removed admin"
            messages.success(request, f"Admin privileges {status} for {user_detail.username}.")
            
        elif action == 'delete_user':
            if user_detail == request.user:
                messages.error(request, "You cannot delete your own account.")
            else:
                username = user_detail.username
                user_detail.delete()
                messages.success(request, f"User {username} has been deleted.")
                return redirect('admin_all_users')
        
        return redirect('admin_user_detail', user_id=user_id)
    
    context = {
        'user_detail': user_detail,
        'profile': profile,
        'releases': releases,
        'followers': followers,
        'following': following,
        'likes': likes,
        'total_releases': releases.count(),
    }
    
    return render(request, "admin/admin_user_detail.html", context)

@login_required(login_url='login')
def admin_apply(request):
    """Apply to become an admin"""
    # Check if user already has a pending request
    existing_request = AdminRequest.objects.filter(user=request.user, status='pending').first()
    if existing_request:
        messages.warning(request, "You already have a pending admin request. Please wait for review.")
        return redirect('index')
    
    # Check if user already tried and got rejected recently (optional: cooldown period)
    rejected_request = AdminRequest.objects.filter(user=request.user, status='rejected').order_by('-created_at').first()
    if rejected_request and rejected_request.created_at > timezone.now() - timedelta(days=30):
        messages.warning(request, "Your previous admin request was rejected. You can apply again after 30 days.")
        return redirect('index')
    
    if request.method == "POST":
        reason = request.POST.get('reason')
        experience = request.POST.get('experience')
        
        if not reason:
            messages.error(request, "Please tell us why you want to become an admin.")
            return redirect('admin_apply')
        
        # Create admin request
        admin_request = AdminRequest.objects.create(
            user=request.user,
            reason=reason,
            experience=experience or ''
        )
        
        # Send notification to system admins
        try:
            from django.core.mail import send_mail
            from django.contrib.sites.shortcuts import get_current_site
            
            current_site = get_current_site(request)
            admin_review_link = f"http://{current_site.domain}/bayaplus/staff/admin-requests/"
            
            # Get all staff users
            admin_emails = User.objects.filter(is_staff=True).values_list('email', flat=True)
            
            if admin_emails:
                subject = f"New Admin Request from {request.user.username}"
                message = f"""
                New Admin Request - BayaPlus
                
                User: {request.user.username} ({request.user.email})
                Reason: {reason}
                Experience: {experience or 'Not provided'}
                
                Review and manage requests here:
                {admin_review_link}
                
                This is an automated notification from BayaPlus.
                """
                
                send_mail(
                    subject,
                    message,
                    'BayaPlus Admin <noreply@bayaplus.com>',
                    list(admin_emails),
                    fail_silently=True,
                )
        except Exception as e:
            print(f"Error sending admin request email: {str(e)}")
        
        messages.success(request, "Your admin request has been submitted! You will be notified once reviewed.")
        return redirect('index')
    
    return render(request, "auth/admin_apply.html")


@staff_member_required(login_url='login')
def admin_manage_requests(request):
    """Admin view to manage admin requests"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('index')
    
    # Get all admin requests
    pending_requests = AdminRequest.objects.filter(status='pending').order_by('-created_at')
    approved_requests = AdminRequest.objects.filter(status='approved').order_by('-created_at')[:20]
    rejected_requests = AdminRequest.objects.filter(status='rejected').order_by('-created_at')[:20]
    
    # Stats
    total_requests = AdminRequest.objects.count()
    pending_count = pending_requests.count()
    approved_count = AdminRequest.objects.filter(status='approved').count()
    rejected_count = AdminRequest.objects.filter(status='rejected').count()
    
    context = {
        'pending_requests': pending_requests,
        'approved_requests': approved_requests,
        'rejected_requests': rejected_requests,
        'total_requests': total_requests,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
    }
    
    return render(request, "admin/admin_requests.html", context)


@staff_member_required(login_url='login')
def admin_review_request(request, request_id):
    """Admin view to review a single admin request"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('index')
    
    admin_request = get_object_or_404(AdminRequest, id=request_id)
    
    if request.method == "POST":
        action = request.POST.get('action')
        admin_notes = request.POST.get('admin_notes', '')
        
        if action == 'approve':
            admin_request.status = 'approved'
            admin_request.reviewed_by = request.user
            admin_request.reviewed_at = timezone.now()
            admin_request.save()
            
            # Make user staff/admin
            user = admin_request.user
            user.is_staff = True
            user.save()
            
            # Send approval email to user
            try:
                send_mail(
                    'Admin Request Approved - BayaPlus',
                    f"""
                    Congratulations {user.username}!
                    
                    Your admin request has been approved. You now have admin access to BayaPlus.
                    
                    You can now manage users, releases, and review content.
                    
                    Login to access the admin panel:
                    http://{get_current_site(request).domain}/bayaplus/staff/dashboard/
                    
                    Notes from reviewer:
                    {admin_notes}
                    
                    - BayaPlus Team
                    """,
                    'BayaPlus Admin <noreply@bayaplus.com>',
                    [user.email],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Error sending approval email: {str(e)}")
            
            messages.success(request, f"Admin request from {user.username} has been approved!")
            
        elif action == 'reject':
            admin_request.status = 'rejected'
            admin_request.reviewed_by = request.user
            admin_request.reviewed_at = timezone.now()
            admin_request.save()
            
            # Send rejection email to user
            try:
                send_mail(
                    'Admin Request Update - BayaPlus',
                    f"""
                    Hi {admin_request.user.username},
                    
                    Your admin request for BayaPlus has been reviewed.
                    
                    Status: Rejected
                    
                    Notes from reviewer:
                    {admin_notes or 'No specific reason provided'}
                    
                    You can apply again after 30 days if you wish.
                    
                    - BayaPlus Team
                    """,
                    'BayaPlus Admin <noreply@bayaplus.com>',
                    [admin_request.user.email],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Error sending rejection email: {str(e)}")
            
            messages.success(request, f"Admin request from {admin_request.user.username} has been rejected.")
            
        elif action == 'delete':
            admin_request.delete()
            messages.success(request, "Admin request has been deleted.")
        
        return redirect('admin_manage_requests')
    
    context = {
        'admin_request': admin_request,
    }
    
    return render(request, "admin/admin_request_review.html", context)


# In views.py - Update the get_track_audio function
# In views.py - Update the streaming function

# In views.py - Streaming functions
def get_track_audio(request, track_id):
    """Stream audio file with range request support"""
    try:
        track = get_object_or_404(Track, id=track_id)
        
        # Check if track is from a published release
        if track.release.status != 'published' or not track.release.is_public:
            return HttpResponse("Track not available", status=404)
        
        audio_file = track.audio_file
        if not audio_file:
            return HttpResponse("Audio file not found", status=404)
        
        # Get the file path
        file_path = audio_file.path
        
        # Check if file exists
        import os
        if not os.path.exists(file_path):
            return HttpResponse("Audio file not found on server", status=404)
        
        # Serve the file
        from django.http import FileResponse
        import mimetypes
        
        # Determine content type
        content_type = mimetypes.guess_type(file_path)[0] or 'audio/mpeg'
        
        # Open the file and return as response
        response = FileResponse(
            open(file_path, 'rb'),
            content_type=content_type
        )
        response['Content-Length'] = os.path.getsize(file_path)
        response['Accept-Ranges'] = 'bytes'
        
        # Handle range requests (for seeking)
        range_header = request.META.get('HTTP_RANGE', '').strip()
        if range_header:
            import re
            range_match = re.search(r'bytes=(\d+)-(\d*)', range_header)
            if range_match:
                start = int(range_match.group(1))
                file_size = os.path.getsize(file_path)
                end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
                
                if start < file_size and end < file_size:
                    response = HttpResponse(
                        open(file_path, 'rb').read(end - start + 1),
                        status=206,
                        content_type=content_type
                    )
                    response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
                    response['Content-Length'] = str(end - start + 1)
                    response['Accept-Ranges'] = 'bytes'
        
        return response
        
    except Exception as e:
        print(f"Stream error: {e}")
        return HttpResponse(f"Error: {str(e)}", status=500)

def track_info(request, track_id):
    """Get track information for playback"""
    try:
        track = get_object_or_404(Track, id=track_id)
        
        # Check if track has audio file
        if not track.audio_file:
            return JsonResponse({
                'error': 'No audio file found for this track',
                'id': track.id,
                'title': track.title
            }, status=404)
        
        # Get release info
        release = track.release
        
        data = {
            'id': track.id,
            'title': track.title,
            'artist': release.artist_profile.artist_name if release.artist_profile else release.artist.username,
            'duration': track.duration or '--',
            'cover_art': release.cover_art.url if release.cover_art else None,
            'release_id': release.id,
            'release_title': release.title,
            'audio_url': f'/bayaplus/stream/{track.id}/',
        }
        
        return JsonResponse(data)
        
    except Track.DoesNotExist:
        return JsonResponse({'error': 'Track not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required(login_url='login')
def track_play_start(request, track_id):
    """Track when a user starts playing a track"""
    if request.method == "POST":
        track = get_object_or_404(Track, id=track_id)
        
        # Create play history entry
        play_history = PlayHistory.objects.create(
            user=request.user,
            track=track,
            duration_played=0,
            completed=False
        )
        
        return JsonResponse({
            'success': True,
            'play_id': play_history.id,
            'track_id': track.id,
            'message': 'Play started'
        })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required(login_url='login')
def track_play_update(request, play_id):
    """Update play progress and count as stream if 30+ seconds played"""
    if request.method == "POST":
        import json
        data = json.loads(request.body)
        play_history = get_object_or_404(PlayHistory, id=play_id, user=request.user)
        duration_played = int(data.get('duration_played', 0))
        completed = data.get('completed', False)
        
        # Update play history
        play_history.duration_played = duration_played
        play_history.completed = completed
        play_history.save()
        
        # If played 30+ seconds, count as a stream
        counted_as_stream = False
        if duration_played >= 30:
            # Increment track plays
            track = play_history.track
            track.plays += 1
            track.save()
            
            # Update release plays
            release = track.release
            release.total_plays += 1
            release.save()
            
            counted_as_stream = True
        
        return JsonResponse({
            'success': True,
            'duration_played': duration_played,
            'counted_as_stream': counted_as_stream,
            'message': 'Play progress updated'
        })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

def release_tracks(request, release_id):
    """Get all tracks for a release"""
    try:
        release = get_object_or_404(Release, id=release_id)
        
        if release.status != 'published' or not release.is_public:
            return JsonResponse({'error': 'Release not available'}, status=404)
        
        tracks = release.tracks.all().order_by('track_number')
        
        data = {
            'release_id': release.id,
            'release_title': release.title,
            'tracks': [
                {
                    'id': track.id,
                    'title': track.title,
                    'artist': release.artist_profile.artist_name if release.artist_profile else release.artist.username,
                    'duration': track.duration or '--',
                    'cover_art': release.cover_art.url if release.cover_art else None,
                    'track_number': track.track_number,
                    'has_audio': bool(track.audio_file),
                }
                for track in tracks
            ]
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
@login_required(login_url='login')
def get_queue(request):
    """Get user's current queue"""
    try:
        queue = Queue.objects.get(user=request.user)
        queue_items = QueueItem.objects.filter(queue=queue).select_related('track', 'track__release')
        
        tracks_data = []
        for item in queue_items:
            track = item.track
            tracks_data.append({
                'id': track.id,
                'title': track.title,
                'artist': track.release.artist_profile.artist_name or track.release.artist.username,
                'duration': track.duration or '--',
                'cover_art': track.release.cover_art.url if track.release.cover_art else None,
                'position': item.position,
                'is_current': item.position == queue.current_index,
                'release_id': track.release.id,
            })
        
        current_data = None
        if queue_items:
            current_item = queue_items.filter(position=queue.current_index).first()
            if current_item:
                track = current_item.track
                current_data = {
                    'id': track.id,
                    'title': track.title,
                    'artist': track.release.artist_profile.artist_name or track.release.artist.username,
                    'duration': track.duration or '--',
                    'cover_art': track.release.cover_art.url if track.release.cover_art else None,
                    'release_id': track.release.id,
                }
        
        return JsonResponse({
            'queue': tracks_data,
            'current': current_data,
            'total': len(tracks_data),
        })
        
    except Queue.DoesNotExist:
        return JsonResponse({'queue': [], 'current': None, 'total': 0})
    
# In views.py - Add a test view
# In views.py - Add this test view
def api_test(request):
    """Test API endpoint"""
    try:
        tracks = Track.objects.all()
        track_data = []
        for track in tracks[:5]:
            track_data.append({
                'id': track.id,
                'title': track.title,
                'has_audio': bool(track.audio_file),
                'release_status': track.release.status,
            })
        
        return JsonResponse({
            'status': 'ok',
            'message': 'API is working',
            'tracks_count': Track.objects.count(),
            'tracks_with_audio': Track.objects.filter(audio_file__isnull=False).count(),
            'sample_tracks': track_data,
            'urls': {
                'track_info': '/bayaplus/api/track/{id}/info/',
                'stream': '/bayaplus/stream/{id}/',
                'play_start': '/bayaplus/api/track/{id}/play/start/',
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    

def all_artists(request):
    """View all artists with trending at the top"""
    # Get all artist profiles with release counts
    artist_profiles = UserProfile.objects.filter(role='Artist')
    
    # Annotate with release count and follower count
    artist_data = []
    for profile in artist_profiles:
        releases = Release.objects.filter(artist=profile.user, status='published', is_public=True)
        followers = Follow.objects.filter(following=profile.user).count()
        
        # Check if current user follows this artist
        is_following = False
        if request.user.is_authenticated:
            is_following = Follow.objects.filter(
                follower=request.user,
                following=profile.user
            ).exists()
        
        artist_data.append({
            'user': profile.user,
            'artist_name': profile.artist_name or profile.user.username,
            'avatar': profile.avatar,
            'release_count': releases.count(),
            'follower_count': followers,
            'is_following': is_following,
            'bio': profile.bio,
            'social_links': profile.get_social_links(),
        })
    
    # Sort by follower count for trending
    trending_artists = sorted(artist_data, key=lambda x: x['follower_count'], reverse=True)[:10]
    
    # Get followed artists for sidebar
    followed_artists = []
    if request.user.is_authenticated:
        followed_artists = Follow.objects.filter(
            follower=request.user
        ).select_related('following', 'following__userprofile')
    
    # Paginate all artists
    paginator = Paginator(artist_data, 24)  # 24 artists per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'trending_artists': trending_artists,
        'all_artists': page_obj,
        'total_artists': len(artist_data),
        'followed_artists': followed_artists,
    }
    
    return render(request, "artist/all_artists.html", context)