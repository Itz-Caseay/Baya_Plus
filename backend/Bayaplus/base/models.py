from django.db import models
from django.contrib.auth.models import AbstractUser

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