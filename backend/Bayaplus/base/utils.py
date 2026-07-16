from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site

class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return (
            str(user.pk) + str(timestamp) + str(user.is_active)
        )

account_activation_token = AccountActivationTokenGenerator()

def send_admin_release_notification(request, release):
    """Send email notification to admins when a new release is created"""
    
    # Generate admin approval link
    current_site = get_current_site(request)
    admin_approval_link = f"http://{current_site.domain}/bayaplus/admin/review-release/{release.id}/"
    
    # Prepare email content
    subject = f"New Release Pending Approval: {release.title}"
    
    # Plain text version
    text_content = f"""
    New Release Notification - BayaPlus Admin
    
    A new release has been submitted for review.
    
    Release Details:
    ---------------
    Title: {release.title}
    Artist: {release.artist_profile.artist_name or release.artist.username}
    Type: {release.get_release_type_display()}
    Genre: {release.genre or 'Not specified'}
    Release Date: {release.release_date}
    Tracks: {release.tracks.count()}
    Status: {release.status}
    
    Description:
    {release.description or 'No description provided'}
    
    To review this release, click the link below:
    {admin_approval_link}
    
    This is an automated notification from BayaPlus.
    """
    
    # HTML version
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333; }}
            .header {{ background: linear-gradient(135deg, #4CAF50, #45a049); color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ padding: 30px; background: #f9f9f9; border-radius: 0 0 10px 10px; }}
            .details {{ background: white; padding: 20px; border-radius: 5px; margin: 15px 0; }}
            .detail-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee; }}
            .label {{ font-weight: bold; color: #555; }}
            .value {{ color: #333; }}
            .btn {{ display: inline-block; padding: 12px 30px; background: #4CAF50; color: white; text-decoration: none; border-radius: 5px; font-weight: bold; }}
            .btn:hover {{ background: #45a049; }}
            .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            .status-badge {{ display: inline-block; padding: 5px 15px; background: #ff9800; color: white; border-radius: 20px; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎵 BayaPlus - New Release</h1>
        </div>
        <div class="content">
            <h2>📢 New Release Pending Approval</h2>
            <p>A new release has been submitted for review by <strong>{release.artist_profile.artist_name or release.artist.username}</strong>.</p>
            
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
                    <span class="label">Release Date:</span>
                    <span class="value">{release.release_date}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Tracks:</span>
                    <span class="value">{release.tracks.count()}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Status:</span>
                    <span class="value"><span class="status-badge">Pending Review</span></span>
                </div>
                {f'''
                <div class="detail-row">
                    <span class="label">Description:</span>
                    <span class="value">{release.description}</span>
                </div>
                ''' if release.description else ''}
            </div>
            
            <p style="text-align: center; margin: 30px 0;">
                <a href="{admin_approval_link}" class="btn">📋 Review Release</a>
            </p>
            
            <p>To review this release, click the button above or copy this link:</p>
            <p style="background: #f0f0f0; padding: 10px; word-break: break-all; border-radius: 5px; font-family: monospace; font-size: 14px;">
                {admin_approval_link}
            </p>
        </div>
        <div class="footer">
            <p>&copy; 2026 BayaPlus. All rights reserved.</p>
            <p>This is an automated notification from BayaPlus.</p>
        </div>
    </body>
    </html>
    """
    
    try:
        # Send email to all admins
        msg = EmailMultiAlternatives(
            subject,
            text_content,
            settings.ADMIN_NOTIFICATION_EMAIL,
            settings.ADMIN_EMAILS,
            bcc=settings.ADMIN_EMAILS,  # Send to all admins
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        return True
    except Exception as e:
        print(f"Error sending admin notification: {str(e)}")
        return False