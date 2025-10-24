import uuid
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


# Assuming you have a UserProfile model already





# In main_app/models.py
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    college_name = models.CharField(max_length=500)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    instagram_access_token = models.CharField(max_length=255, blank=True, null=True)
    instagram_user_id = models.CharField(max_length=50, blank=True, null=True, unique=True)
    # CRITICAL: This default=False is what enforces the mandatory setup.
    setup_complete = models.BooleanField(default=False)

    profile_icon = models.ImageField(
        upload_to='profile_icons/',
        null=True,
        blank=True
    )

    def __str__(self):
        return self.user.username


# --- (Other models like Post, Event, EventApplicationDetails, etc. go here) ---



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

    SCREENING_CHOICES = [
        ('none', 'No Screening'),
        ('aptitude', 'Aptitude Test'),
        ('video', 'Video Screening'),
        ('photo', 'Photo Screening'),
    ]

    # ⭐ NEW FIELD: Use a CharField for the screening choice
    screening_type = models.CharField(
        max_length=10,
        choices=SCREENING_CHOICES,
        default='none',
        verbose_name='Screening Round Type'
    )

    def __str__(self):
        return self.event_name


# ... (after the Event model)

class AptitudeTest(models.Model):
    """Stores the main details for an aptitude test tied to an Event."""

    # CRITICAL: One-to-one link to the Event. Every event can have at most one test.
    event = models.OneToOneField(
        'Event',
        on_delete=models.CASCADE,
        related_name='aptitude_test'
    )

    # 1. Stores the total time limit in minutes
    time_limit_minutes = models.IntegerField(
        default=30,
        verbose_name='Time Limit (Minutes)'
    )

    # 2. Stores the date/time the test should be available to applicants
    test_start_date_time = models.DateTimeField(
        verbose_name='Test Start Date and Time'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Aptitude Test for {self.event.event_name}"


class AptitudeQuestion(models.Model):
    """Stores the individual Multiple Choice Questions for a test."""

    # Link to the Test Header (one AptitudeTest has many Questions)
    test = models.ForeignKey(
        'AptitudeTest',
        on_delete=models.CASCADE,
        related_name='questions'
    )

    question_text = models.TextField()

    # Stores the options for the MCQ
    option_a = models.CharField(max_length=500)
    option_b = models.CharField(max_length=500)
    option_c = models.CharField(max_length=500)
    option_d = models.CharField(max_length=500)

    # Stores the correct answer (A, B, C, or D)
    # Choices make sure the data is valid
    ANSWER_CHOICES = [
        ('A', 'Option A'),
        ('B', 'Option B'),
        ('C', 'Option C'),
        ('D', 'Option D'),
    ]
    correct_answer = models.CharField(
        max_length=1,
        choices=ANSWER_CHOICES
    )

    # Scoring (simple points per question)
    points = models.IntegerField(default=1)

    def __str__(self):
        return f"Q{self.id}: {self.question_text[:30]}..."



class EventApplicationDetails(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    college_name = models.CharField(max_length=500)
    whatsapp_number = models.CharField(max_length=20, null=True, blank=True)
    email_id = models.EmailField()
    applied_at = models.DateTimeField(auto_now_add=True)
    is_shortlisted = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'event')

    def __str__(self):
        return f"{self.name} applied to {self.event.event_name}"


class AptitudeTestAttempt(models.Model):
    """Tracks a user's attempt at an AptitudeTest and stores their score."""

    # Link to the user who took the test
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='test_attempts'
    )

    # Link to the specific test/event
    test = models.ForeignKey(
        'AptitudeTest',
        on_delete=models.CASCADE,
        related_name='attempts'
    )

    # Tracks the total time taken (in seconds)
    time_taken_seconds = models.IntegerField(
        null=True,
        blank=True
    )

    # The final calculated score
    score = models.IntegerField(default=0)

    # Timestamp of when the test was submitted
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # A user can only attempt a specific test once
        unique_together = ('user', 'test')

    def __str__(self):
        return f"{self.user.username}'s score for {self.test.event.event_name}: {self.score}"



# Add these two new classes after EventApplicationDetails model

class VideoScreeningSubmission(models.Model):
    """Stores the video file submission for a registered user."""
    # Using OneToOneField here is simpler if we assume a user can submit one file per event application
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='video_submissions') # Changed to ForeignKey
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    video_file = models.FileField(upload_to='event_videos/')
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'event')
        verbose_name = "Video Submission"

    def __str__(self):
        return f"Video by {self.user.username} for {self.event.event_name}"


class PhotoScreeningSubmission(models.Model):
    """Stores the photo file submission for a registered user."""
    # Using OneToOneField here is simpler if we assume a user can submit one file per event application
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='photo_submissions') # Changed to ForeignKey
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    photo_file = models.ImageField(upload_to='event_photos/')
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'event')
        verbose_name = "Photo Submission"

    def __str__(self):
        return f"Photo by {self.user.username} for {self.event.event_name}"



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



# ----------------------------------------------------------------------
# ✅ CORRECTED SIGNAL HANDLERS FOR PROFILE CREATION/ENFORCEMENT
# ----------------------------------------------------------------------

@receiver(post_save, sender=User)
def manage_user_profile(sender, instance, created, **kwargs):
    """
    Handles user profile creation on user creation and saves on user updates.
    """
    if created:
        # CRITICAL FIX 1: Explicitly pass a default for the required field
        # 'college_name' to prevent database errors.
        UserProfile.objects.create(
            user=instance,
            college_name="Not Set (Mandatory Setup)", # Use a clear default
            setup_complete=False
        )
    else:
        # CRITICAL FIX 2: Check if the profile exists BEFORE trying to save it.
        # This prevents the UNIQUE constraint error.
        try:
            instance.userprofile.save()
        except UserProfile.DoesNotExist:
            # This path should ideally never be hit, but acts as a safeguard.
            pass



class ChatMessage(models.Model):
    """Stores messages for college-specific chat rooms."""

    # The 'college_room_slug' is the sanitized name used for Channels routing (e.g., 'kristu_jayanti')
    college_room_slug = models.CharField(max_length=255, db_index=True)

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # Text is optional if a file is uploaded
    content = models.TextField(blank=True, null=True)

    # FileField to store media (photos/videos)
    media_file = models.FileField(upload_to='chat_media/', blank=True, null=True)

    # Type allows easy distinction in frontend
    MESSAGE_TYPES = [
        ('text', 'Text'),
        ('media', 'Media'),
    ]
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default='text')

    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f'{self.user.username} in {self.college_room_slug} at {self.timestamp.strftime("%H:%M")}'

    class Meta:
        ordering = ['timestamp']




# Add this new class:
class State(models.Model):
    """Stores a clean, canonical list of state names."""
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name