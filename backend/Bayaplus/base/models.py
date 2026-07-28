from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

# Create your models here.

class User(AbstractUser):
    fullname = models.CharField(max_length=50, blank=False, null=False)
    email = models.EmailField(max_length=254, unique=True, blank=False)
    username = models.CharField(max_length=50, unique=True, blank=False, null=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.username} registered on {self.date_joined}"
    
    
class UserProfile(models.Model):
    ROLES = (
        ('Artist', 'Artist'),
        ('Fan', 'Fan'),
        # No Admin role needed - admins use is_staff flag
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLES, blank=False)
    artist_name = models.CharField(max_length=50, unique=True, blank=True, null=True)
    email_verified = models.BooleanField(default=False)
    payment_verified = models.BooleanField(default=False)
    
    # Profile fields for all users (including admins)
    bio = models.TextField(blank=True, null=True, max_length=500)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    
    # Social links (for artists)
    instagram = models.URLField(blank=True, null=True, max_length=200)
    twitter = models.URLField(blank=True, null=True, max_length=200)
    tiktok = models.URLField(blank=True, null=True, max_length=200)
    youtube = models.URLField(blank=True, null=True, max_length=200)
    spotify = models.URLField(blank=True, null=True, max_length=200)
    apple_music = models.URLField(blank=True, null=True, max_length=200)
    soundcloud = models.URLField(blank=True, null=True, max_length=200)
    facebook = models.URLField(blank=True, null=True, max_length=200)
    website = models.URLField(blank=True, null=True, max_length=200)
    
    def __str__(self):
        return f"{self.user.username} role: {self.role}"
    
    def get_social_links(self):
        """Return a dictionary of social links"""
        return {
            'instagram': self.instagram,
            'twitter': self.twitter,
            'tiktok': self.tiktok,
            'youtube': self.youtube,
            'spotify': self.spotify,
            'apple_music': self.apple_music,
            'soundcloud': self.soundcloud,
            'facebook': self.facebook,
            'website': self.website,
        }
    
    def has_social_links(self):
        """Check if any social links are set"""
        links = self.get_social_links()
        return any(link for link in links.values())

class AdminRequest(models.Model):
    """Model for users requesting admin access"""
    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='admin_requests')
    reason = models.TextField(max_length=500, help_text="Why do you want to become an admin?")
    experience = models.TextField(max_length=500, blank=True, null=True, help_text="Relevant experience")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_admin_requests')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - Admin Request ({self.status})"
 
class Release(models.Model):
    # Release Types
    RELEASE_TYPES = (
        ('single', 'Single'),
        ('ep', 'EP'),
        ('album', 'Album'),
        ('mixtape', 'Mixtape'),
        ('compilation', 'Compilation'),
        ('remix', 'Remix'),
        ('live', 'Live Recording'),
    )
    
    # Release Status
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('pending', 'Pending Review'),
        ('published', 'Published'),
        ('archived', 'Archived'),
        ('rejected', 'Rejected'),
    )
    
    # Basic Information
    title = models.CharField(max_length=200, blank=False, null=False)
    artist = models.ForeignKey(User, on_delete=models.CASCADE, related_name='releases')
    artist_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='releases', null=True, blank=True)
    
    # Release Details
    release_type = models.CharField(max_length=20, choices=RELEASE_TYPES, default='single')
    genre = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    
    # Album Art - ONE per release (3000x3000)
    cover_art = models.ImageField(
        upload_to='release_covers/', 
        blank=True, 
        null=True, 
        help_text="3000x3000 pixels recommended. JPG or PNG format."
    )
    
    # Release Dates
    release_date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Track Information
    track_count = models.PositiveIntegerField(default=0)
    duration = models.CharField(max_length=20, blank=True, null=True)  # Total duration as "MM:SS"
    
    # Status and Visibility
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_public = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    
    # Metadata
    tags = models.CharField(max_length=500, blank=True, null=True)
    language = models.CharField(max_length=50, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    
    # Statistics
    total_plays = models.PositiveIntegerField(default=0)
    total_likes = models.PositiveIntegerField(default=0)
    total_comments = models.PositiveIntegerField(default=0)
    total_shares = models.PositiveIntegerField(default=0)
    
    # Monetization
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_free = models.BooleanField(default=True)
    
    # Featured Track (if album/EP)
    featured_track = models.CharField(max_length=200, blank=True, null=True)
    
    # Collaborators
    collaborators = models.ManyToManyField(User, related_name='collaborations', blank=True)
    
    # Social Media
    youtube_link = models.URLField(max_length=200, blank=True, null=True)
    spotify_link = models.URLField(max_length=200, blank=True, null=True)
    apple_music_link = models.URLField(max_length=200, blank=True, null=True)
    
    class Meta:
        ordering = ['-release_date', '-created_at']
        indexes = [
            models.Index(fields=['artist', 'status', 'release_date']),
            models.Index(fields=['release_type', 'status']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.artist.username}"
    
    @property
    def is_new_release(self):
        """Check if release is from the last 30 days"""
        return (timezone.now().date() - self.release_date).days <= 30


class Track(models.Model):
    """Individual tracks within a release - each has its own audio file"""
    release = models.ForeignKey(Release, on_delete=models.CASCADE, related_name='tracks')
    title = models.CharField(max_length=200)
    track_number = models.PositiveIntegerField()
    duration = models.CharField(max_length=20, blank=True, null=True, help_text="MM:SS format")
    
    # Audio file for THIS track
    audio_file = models.FileField(
        upload_to='tracks/audio/', 
        blank=True, 
        null=True,
        help_text="MP3, WAV, or FLAC format"
    )
    
    lyrics = models.TextField(blank=True, null=True)
    is_explicit = models.BooleanField(default=False)
    
    # Statistics - This field already exists
    plays = models.PositiveIntegerField(default=0)  # This is the field causing the conflict
    
    class Meta:
        ordering = ['track_number']
        unique_together = ['release', 'track_number']
    
    def __str__(self):
        return f"{self.track_number}. {self.title} - {self.release.title}"

class Like(models.Model):
    """Track or Release likes"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    release = models.ForeignKey(Release, on_delete=models.CASCADE, related_name='likes', null=True, blank=True)
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name='likes', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [['user', 'release'], ['user', 'track']]
        indexes = [
            models.Index(fields=['user', 'release']),
            models.Index(fields=['user', 'track']),
        ]
    
    def __str__(self):
        if self.release:
            return f"{self.user.username} likes {self.release.title}"
        if self.track:
            return f"{self.user.username} likes {self.track.title}"
        return f"{self.user.username} liked something"


class Comment(models.Model):
    """Comments on releases"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    release = models.ForeignKey(Release, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    is_approved = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username}: {self.content[:50]}..."

class Playlist(models.Model):
    """User playlists"""
    name = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='playlists')
    releases = models.ManyToManyField(Release, related_name='playlists', blank=True)
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cover_art = models.ImageField(upload_to='playlist_covers/', blank=True, null=True)
    
    class Meta:
        unique_together = ['user', 'name']
    
    def __str__(self):
        return f"{self.name} - {self.user.username}"
    
    
class Follow(models.Model):
    """Artist follow relationship"""
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['follower', 'following']
        indexes = [
            models.Index(fields=['follower', 'following']),
        ]
    
    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"
    

# In models.py - Add Streaming models

# In models.py - Fix the PlayHistory model

class PlayHistory(models.Model):
    """Track user's listening history"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='play_history')
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name='play_history')  # Changed related_name
    played_at = models.DateTimeField(auto_now_add=True)
    duration_played = models.IntegerField(default=0)  # seconds played
    completed = models.BooleanField(default=False)  # if they listened to the whole track
    
    class Meta:
        ordering = ['-played_at']
    
    def __str__(self):
        return f"{self.user.username} played {self.track.title}"


class Queue(models.Model):
    """User's playback queue"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='queue')
    tracks = models.ManyToManyField(Track, through='QueueItem')
    current_index = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Queue"


class QueueItem(models.Model):
    """Individual items in the queue"""
    queue = models.ForeignKey(Queue, on_delete=models.CASCADE, related_name='queue_items')
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name='queue_items')
    position = models.IntegerField()
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['position']
        unique_together = ['queue', 'position']
    
    def __str__(self):
        return f"{self.track.title} at position {self.position}"