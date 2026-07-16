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
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLES, blank=False)
    artist_name = models.CharField(max_length=50, unique=True, blank=True, null=True)
    email_verified = models.BooleanField(default=False)
    payment_verified = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.user.username} role: {self.role}"
    
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
    cover_art = models.ImageField(upload_to='release_covers/', blank=True, null=True)
    
    # Release Dates
    release_date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Track Information
    track_count = models.PositiveIntegerField(default=1)
    duration = models.DurationField(blank=True, null=True)  # Total duration
    
    # Audio Files
    audio_file = models.FileField(upload_to='releases/audio/', blank=True, null=True)
    
    # Status and Visibility
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_public = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    
    # Metadata
    tags = models.CharField(max_length=500, blank=True, null=True)  # Comma separated tags
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
    
    # Featured Tracks (if album/EP)
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
    
    @property
    def formatted_duration(self):
        """Return duration in HH:MM:SS format"""
        if self.duration:
            total_seconds = int(self.duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            if hours > 0:
                return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            return f"{minutes:02d}:{seconds:02d}"
        return "00:00"
    
    @property
    def display_artist_name(self):
        """Return artist name from profile or username"""
        if self.artist_profile and self.artist_profile.artist_name:
            return self.artist_profile.artist_name
        return self.artist.username


class Track(models.Model):
    """Individual tracks within a release"""
    release = models.ForeignKey(Release, on_delete=models.CASCADE, related_name='tracks')
    title = models.CharField(max_length=200)
    track_number = models.PositiveIntegerField()
    duration = models.CharField(max_length=20, blank=True, null=True)  # Store as "3:45"
    audio_file = models.FileField(upload_to='tracks/audio/', blank=True, null=True)  # ← Add this
    lyrics = models.TextField(blank=True, null=True)
    is_explicit = models.BooleanField(default=False)
    
    # Statistics
    plays = models.PositiveIntegerField(default=0)
    
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