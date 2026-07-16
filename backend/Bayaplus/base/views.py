from django.shortcuts import render, redirect
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
from django.conf import settings
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

def artistboard(request):
    profile = UserProfile.objects.get(user=request.user)
    return HttpResponse(f"""
                       <h2>Welcome, { request.user.username }</h2> 
                       <h3>Role: {profile.role}</h3> 
                       <h3>Email Verified: {profile.email_verified}</h3>
                       <h3>Payment Verified: {profile.payment_verified}</h3>
                       <p><a href="/bayaplus/logout/">Logout</a></p>"""
                        )