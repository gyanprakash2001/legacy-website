import uuid
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    college_name = models.CharField(max_length=500)
    profile_icon = models.ImageField(
        upload_to='profile_icons/',
        null=True,
        blank=True
    )

    def __str__(self):
        return self.user.username

class Post(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    post_text = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Post by {self.author.username}'

class MediaFile(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='media_files')
    file = models.FileField(upload_to='post_media/')
    file_type = models.CharField(max_length=10, default='image')

    def __str__(self):
        return f"Media for Post {self.post.id}"

class Event(models.Model):
    event_name = models.CharField(max_length=200)
    event_type = models.ForeignKey(
        'EventType', on_delete=models.SET_NULL, null=True
    )
    event_banner = models.ImageField(
        upload_to='event_banners/',
        null=True,
        blank=True,
        verbose_name='Event Banner Image (Optional)'
    )
    description = models.TextField(default="No description provided.")
    location = models.CharField(max_length=250)
    state = models.CharField(max_length=100, blank=True, null=True)
    date_time = models.DateTimeField()
    registration_fees = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    organizer = models.ForeignKey(User, on_delete=models.CASCADE)
    event_link_key = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    show_phone_number_on_query = models.BooleanField(default=True)

    def __str__(self):
        return self.event_name

class EventApplicationDetails(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    college_name = models.CharField(max_length=500)
    whatsapp_number = models.CharField(max_length=20, null=True, blank=True)
    email_id = models.EmailField()
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'event')

    def __str__(self):
        return f"{self.name} applied to {self.event.event_name}"

class Follow(models.Model):
    follower = models.ForeignKey(User, related_name='following', on_delete=models.CASCADE)
    college_name = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'college_name')

    def __str__(self):
        return f"{self.follower.username} follows {self.college_name}"

class College(models.Model):
    name = models.CharField(max_length=500, unique=True)
    state = models.CharField(max_length=200, null=True, blank=True)
    def __str__(self):
        return self.name


class EventCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class EventType(models.Model):
    category = models.ForeignKey(EventCategory, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.category.name} - {self.name}"