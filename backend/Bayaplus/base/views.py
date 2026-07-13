from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage, send_mail
# from django.template.loader import render_to_string
from .models import *

# Create your views here.

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
                
                # Print link to console for development
                print("\n" + "="*60)
                print("🔗 VERIFICATION LINK:")
                print(verification_link)
                print("="*60 + "\n")
                
                # Send verification email
                mail_subject = 'Activate your account'
                message = render_to_string('auth/acc_active_email.html', {
                    'user': user,
                    'domain': current_site.domain,
                    'uid': uid,
                    'token': token,
                })
                to_email = email
                email_message = EmailMessage(mail_subject, message, to=[to_email])
                email_message.send()
                
                return HttpResponse(f"""
                    <h2>Registration Successful!</h2>
                    <p>A verification email has been sent to <strong>{email}</strong></p>
                    <p><strong>📧 Check your console/terminal for the verification link</strong></p>
                    <p><a href="/bayaplus/login/">Go to Login</a></p>
                """)
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
            # Profile doesn't exist yet (will be created during choose-profile)
            pass
        
        messages.success(request, "Thank you for confirming your email. You can now login and create your profile.")
        return redirect('login')
    else:
        messages.error(request, "Activation link is invalid or expired!")
        return redirect('signup')

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

            # Check whether the user has created a profile
            try:
                profile = UserProfile.objects.get(user=user)

                # Check if email is verified
                if not profile.email_verified:
                    messages.warning(request, "Your email is not verified. Please check your inbox for the verification link.")
                    # Still allow login but show warning
                
                messages.success(request, f"Welcome back, {user.username}!")

                # Redirect according to profile role
                if profile.role == "Artist":
                    return redirect("artistboard")
                elif profile.role == "Fan":
                    return redirect("fanboard")
                else:
                    # Fallback if role is neither Artist nor Fan
                    return redirect("index")

            except UserProfile.DoesNotExist:
                # Redirect to choose-profile if no profile exists
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
    # Check if user is authenticated
    if not request.user.is_authenticated:
        messages.error(request, "Please login first.")
        return redirect('login')
    
    # Check if user already has a profile
    if UserProfile.objects.filter(user=request.user).exists():
        messages.error(request, "You already have a profile")
        return redirect('index')
    
    if request.method == "POST":
        role = request.POST.get("role")

        if role == "Artist":
            artist_name = request.POST.get("artist_name")
            
            # Check if artist_name is provided
            if not artist_name:
                messages.error(request, "Artist name is required.")
                return redirect("choose-profile")

            if UserProfile.objects.filter(artist_name=artist_name).exists():
                messages.error(request, "Artist name already taken. Choose another")
                return redirect("choose-profile")

            profile = UserProfile.objects.create(
                user=request.user,
                role=role,
                artist_name=artist_name,
                email_verified=request.user.is_active
            )

            messages.success(request, f"Artist account '{artist_name}' created successfully!")
            return redirect("artistboard")

        elif role == "Fan":
            profile = UserProfile.objects.create(
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
                        <h3>Email Verified: {profile.email_verified}</h3>"""
                        )

def artistboard(request):
    profile = UserProfile.objects.get(user=request.user)
    return HttpResponse(f"""
                       <h2>Welcome, { request.user.username }</h2> 
                       <h3>Role: {profile.role}</h3> 
                       <h3>Email Verified: {profile.email_verified}</h3>
                       <h3>Payment Verified: {profile.payment_verified}</h3>"""
                        )