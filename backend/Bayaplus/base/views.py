from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives, send_mail
from django.contrib.auth.tokens import default_token_generator
from .utils import *
from django.conf import settings
from datetime import timedelta
import re
from .models import *
import logging

logger = logging.getLogger(__name__)

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
                    
                    # Create email content
                    mail_subject = 'Activate Your BayaPlus Account'
                    
                    # Plain text version
                    text_content = f"""
                    Hi {user.fullname},

                    Welcome to BayaPlus! Please confirm your email address to activate your account.

                    Click the link below to verify your email:
                    {verification_link}

                    If you didn't create an account with BayaPlus, please ignore this email.

                    Thanks,
                    The BayaPlus Team
                    """
                    
                    # HTML version
                    html_content = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <style>
                            body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333; }}
                            .header {{ background: #4CAF50; color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }}
                            .content {{ padding: 30px; background: #f9f9f9; border-radius: 0 0 10px 10px; }}
                            .btn {{ display: inline-block; padding: 12px 30px; background: #4CAF50; color: white; text-decoration: none; border-radius: 5px; font-weight: bold; }}
                            .btn:hover {{ background: #45a049; }}
                            .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
                            .link {{ background: #f0f0f0; padding: 10px; word-break: break-all; border-radius: 5px; font-family: monospace; }}
                        </style>
                    </head>
                    <body>
                        <div class="header">
                            <h1>🎵 BayaPlus</h1>
                        </div>
                        <div class="content">
                            <h2>Hi {user.fullname},</h2>
                            <p>Welcome to BayaPlus! Please confirm your email address to activate your account.</p>
                            <p style="text-align: center;">
                                <a href="{verification_link}" class="btn">Verify Email Address</a>
                            </p>
                            <p>Or copy and paste this link in your browser:</p>
                            <div class="link">{verification_link}</div>
                            <br>
                            <p>If you didn't create an account with BayaPlus, please ignore this email.</p>
                            <p>This link will expire in 24 hours.</p>
                        </div>
                        <div class="footer">
                            <p>&copy; 2026 BayaPlus. All rights reserved.</p>
                            <p>This is an automated message, please do not reply to this email.</p>
                        </div>
                    </body>
                    </html>
                    """
                    
                    # Send email with both plain text and HTML versions
                    try:
                        msg = EmailMultiAlternatives(
                            mail_subject,
                            text_content,
                            settings.DEFAULT_FROM_EMAIL,
                            [email]
                        )
                        msg.attach_alternative(html_content, "text/html")
                        msg.send()
                        
                        print(f"✅ Verification email sent successfully to {email}")
                        
                        # Return success page
                        return HttpResponse(f"""
                            <!DOCTYPE html>
                            <html>
                            <head>
                                <style>
                                    body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; text-align: center; }}
                                    h2 {{ color: #4CAF50; }}
                                    .btn {{ display: inline-block; padding: 10px 20px; background: #4CAF50; color: white; text-decoration: none; border-radius: 5px; }}
                                    .info {{ background: #e3f2fd; padding: 20px; border-radius: 5px; margin: 20px 0; }}
                                </style>
                            </head>
                            <body>
                                <h2>🎉 Registration Successful!</h2>
                                <div class="info">
                                    <p>📧 A verification email has been sent to <strong>{email}</strong></p>
                                    <p>Please check your inbox (and spam folder) to activate your account.</p>
                                </div>
                                <p><a href="/bayaplus/login/" class="btn">Go to Login</a></p>
                            </body>
                            </html>
                        """)
                        
                    except Exception as e:
                        print(f"❌ Email sending failed: {str(e)}")
                        return HttpResponse(f"""
                            <h2>Registration Successful but Email Failed!</h2>
                            <p>Your account was created but we couldn't send the verification email.</p>
                            <p><strong>Error:</strong> {str(e)}</p>
                            <p>Please contact support or try again later.</p>
                            <p><a href="/bayaplus/login/">Go to Login</a></p>
                        """)
                        
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
                <a href="/bayaplus/login/" class="btn">Login to BayaPlus</a>
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
                    return redirect("artistboard")
                elif profile.role == "Fan":
                    return redirect("fanboard")
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

def fanboard(request):
    profile = UserProfile.objects.get(user=request.user)
    return HttpResponse(f"""
                        <h2>Welcome, { request.user.username }</h2> 
                        <h3>Role: {profile.role}</h3>
                        <h3>Email Verified: {profile.email_verified}</h3>
                        <p><a href="/bayaplus/logout/">Logout</a></p>"""
                        )

@login_required(login_url="login")
def artistboard(request):
    profile = UserProfile.objects.get(user=request.user)
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
    
    if request.method == "POST":
        action = request.POST.get('action')
        
        if action == 'publish':
            # Check if release has tracks
            if release.tracks.count() == 0:
                messages.error(request, "Cannot publish a release without tracks. Please add at least one track.")
                return redirect('add_tracks', release_id=release_id)
            
            # Check if tracks have audio files
            tracks_without_audio = release.tracks.filter(audio_file__isnull=True)
            if tracks_without_audio.exists():
                messages.error(request, f"Please upload audio files for the following tracks: {', '.join([t.title for t in tracks_without_audio])}")
                return redirect('add_tracks', release_id=release_id)
            
            # Check if cover art is uploaded
            if not release.cover_art:
                messages.warning(request, "You haven't uploaded cover art. It's recommended for better visibility.")
            
            # Submit for review
            release.status = 'pending'
            release.is_public = False
            release.save()
            
            # Send notification to admins
            try:
                from django.core.mail import EmailMultiAlternatives
                from django.contrib.sites.shortcuts import get_current_site
                
                current_site = get_current_site(request)
                admin_approval_link = f"http://{current_site.domain}/bayaplus/admin/review-release/{release.id}/"
                
                subject = f"New Release Pending Approval: {release.title}"
                
                text_content = f"""
                New Release Notification - BayaPlus Admin
                
                A new release has been submitted for review.
                
                Title: {release.title}
                Artist: {release.artist_profile.artist_name or release.artist.username}
                Type: {release.get_release_type_display()}
                Tracks: {release.tracks.count()}
                Audio Files: {'✅ Yes' if release.tracks.filter(audio_file__isnull=False).exists() else '❌ No'}
                Cover Art: {'✅ Yes' if release.cover_art else '❌ No'}
                
                Review Link: {admin_approval_link}
                """
                
                html_content = f"""
                <h2>New Release: {release.title}</h2>
                <p><strong>Artist:</strong> {release.artist_profile.artist_name or release.artist.username}</p>
                <p><strong>Type:</strong> {release.get_release_type_display()}</p>
                <p><strong>Tracks:</strong> {release.tracks.count()}</p>
                <p><strong>Audio Files:</strong> {'✅ Yes' if release.tracks.filter(audio_file__isnull=False).exists() else '❌ No'}</p>
                <p><strong>Cover Art:</strong> {'✅ Yes' if release.cover_art else '❌ No'}</p>
                <p><a href="{admin_approval_link}">Click here to review</a></p>
                """
                
                from_email = 'BayaPlus Admin <edutrackplus12@gmail.com>'
                
                msg = EmailMultiAlternatives(
                    subject,
                    text_content,
                    from_email,
                    ['edutrackplus12@gmail.com']
                )
                msg.attach_alternative(html_content, "text/html")
                msg.send()
                
                messages.success(request, f"Release '{release.title}' submitted for admin review!")
                
            except Exception as e:
                print(f"Error sending admin notification: {str(e)}")
                messages.warning(request, f"Release submitted but admin notification failed.")
            
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
    return render(request, "releases/publish_release.html", {
        'release': release,
        'tracks': tracks,
        'track_count': tracks.count(),
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
    """Admin view to review and approve/reject releases"""
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
    return render(request, "admin/review_release.html", {
        'release': release,
        'tracks': tracks,
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
            
            if audio_file:
                messages.success(request, f"Track '{track_title}' added with audio file '{audio_file.name}'!")
            else:
                messages.warning(request, f"Track '{track_title}' added but no audio file uploaded.")
            
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
    """Upload cover art for a release"""
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
        
        release.cover_art = cover_art
        release.save()
        
        messages.success(request, f"Cover art uploaded successfully!")
    
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