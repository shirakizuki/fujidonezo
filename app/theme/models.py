from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.CharField(max_length=255, default='https://api.dicebear.com/7.x/thumbs/png?seed=random')
    is_verified = models.BooleanField(default=False)

# Create user profile when a new user is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

# Save user profile when user is saved
@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

class Labels(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Label"
        verbose_name_plural = "Labels"

class Tasks(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    due_date = models.DateField(null=True, blank=True)
    due_time = models.TimeField(null=True, blank=True)
    labels = models.ManyToManyField(Labels, related_name='tasks', blank=True)
    
    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name = "Task"
        verbose_name_plural = "Tasks"
        
class EmailVerificationToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    last_sent = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Verification token for {self.user.email}"
    
    @property
    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at
        
    @property
    def can_resend(self):
        time_since_last_sent = timezone.now() - self.last_sent
        return time_since_last_sent > timedelta(seconds=90)  # 90 seconds cooldown
        
    def mark_used(self):
        self.is_used = True
        self.save()
        
    def reset_token(self):
        """Reset token with new expiry time and update last sent time"""
        if not self.is_valid:
            self.token = uuid.uuid4()
            self.is_used = False
        self.expires_at = timezone.now() + timedelta(minutes=5)
        self.last_sent = timezone.now()
        self.save()
        
class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    last_sent = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Password reset token for {self.user.email}"
    
    @property
    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at
        
    @property
    def can_resend(self):
        time_since_last_sent = timezone.now() - self.last_sent
        return time_since_last_sent > timedelta(seconds=90)  # 90 seconds cooldown
        
    def mark_used(self):
        self.is_used = True
        self.save()
        
    def reset_token(self):
        """Reset token with new expiry time and update last sent time"""
        if not self.is_valid:
            self.token = uuid.uuid4()
            self.is_used = False
        self.expires_at = timezone.now() + timedelta(minutes=5)
        self.last_sent = timezone.now()
        self.save()