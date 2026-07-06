from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

class User(AbstractUser):
    username = models.CharField(max_length=50, unique=True, blank=False)
    email = models.EmailField(max_length=254, unique=True, blank=False)
    full_name = models.CharField(max_length=50)
    
    def __str__(self):
        return f"User {self.usernaame}"
    
class Profile(models.Model):
    GENDER = (
        ('Male', 'Male'),
        ('Female', 'Female'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    gender = models.CharField(max_length=50, null=False, null=False, choices=GENDER, default="Male")
    is_artist = models.BooleanField(default=False)
    
    def __str__(self):
        return f"User {self.user.username}'s Profile"