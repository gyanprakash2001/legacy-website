# main_app/forms.py

from django import forms
from django.contrib.auth.models import User
from django.forms import ClearableFileInput
from django.core.exceptions import ValidationError
from django.db.models import Q
from .models import UserProfile, Post, Event, EventApplicationDetails, College, AptitudeTest, AptitudeQuestion, VideoScreeningSubmission, PhotoScreeningSubmission
from django.forms import inlineformset_factory

class MultiFileInput(ClearableFileInput):
    def __init__(self, attrs=None):
        super().__init__(attrs)
        self.attrs['multiple'] = 'multiple'


# main_app/forms.py

class UserRegistrationForm(forms.ModelForm):
    # Password confirmation field
    password_confirm = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)

    class Meta:
        model = User
        # CRITICAL CHANGE 1: REMOVE 'username' from fields.
        # Django will now only validate email, password, first_name, and last_name.
        fields = ['email', 'password', 'first_name', 'last_name']
        widgets = {
            'password': forms.PasswordInput(),
        }

    def clean_email(self):
        email = self.cleaned_data['email']

        # --- ROBUST CHECK (Keep this) ---
        # Checks if email is used as EITHER username (old/social) OR email (new)
        # This is correct for checking uniqueness against existing records.
        if User.objects.filter(Q(username__iexact=email) | Q(email__iexact=email)).exists():
            raise ValidationError("A user with that email already exists.")

        # CRITICAL CHANGE 2: Remove manual assignment of 'username' here.
        # It is handled more reliably in the save() method or in the view.
        # Removing this line: self.cleaned_data['username'] = email

        return email

    # ... (rest of the form remains the same) ...

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])

        # CHANGE 3: Keep this logic to ensure username is set to email before saving
        user.username = self.cleaned_data['email']  # Use the cleaned email directly

        if commit:
            user.save()
        return user

class PostForm(forms.ModelForm):
    media_files = forms.FileField(widget=MultiFileInput(), required=False)

    class Meta:
        model = Post
        fields = ['post_text']


class EventCreationForm(forms.ModelForm):
    # 1. NEW FIELD: Event Banner Image
    event_banner = forms.ImageField(required=False, label="Event Banner Image (Recommended)")

    # 2. ENHANCED FIELD: Description with detailed placeholder
    description = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 6}),
        label="Description",
    )

    class Meta:
        model = Event
        fields = [
            'event_name',
            'event_type',
            'description',
            'event_banner',  # Include the Banner field
            'location',
            'state',  # Include the State field
            'date_time',
            'registration_fees',
            'phone_number',
            'show_phone_number_on_query',
            'screening_type'
        ]

        # 3. REMOVE TIME: Use DateInput widget instead of DateTimeInput
        widgets = {
            # This makes Django render a date-only picker (Point 6)
            'date_time': forms.DateInput(attrs={'type': 'date'}),
        }

    # Custom __init__ to set the description placeholder (Point 4)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Detailed guidelines as the placeholder text
        placeholder_text = (
            "This field helps you to mention the details of the opportunity you are listing. "
            "It is better to include Rules, Eligibility, Process, Format, etc., in order to get the opportunity approved. "
            "The more details, the better!\n\n"
            "Guidelines:\n"
            "• Mention all the guidelines like eligibility, format, etc.\n"
            "• Inter-college team members allowed or not.\n"
            "• Inter-specialization team members allowed or not.\n"
            "• The number of questions/ problem statements.\n"
            "• Duration of the rounds.\n\n"
            "Rules:\n"
            "• Mention the rules of the competition."
        )
        self.fields['description'].widget.attrs['placeholder'] = placeholder_text


class EventApplicationForm(forms.ModelForm):
    class Meta:
        model = EventApplicationDetails
        fields = ['name', 'college_name', 'whatsapp_number', 'email_id']


# --- ADD THESE TWO CLASSES TO THE END OF main_app/forms.py ---

class UserUpdateForm(forms.ModelForm):
    """Form for updating core Django User details (name and email)."""
    email = forms.EmailField(label='Email') # Keep email as an editable field

    # CRITICAL: We explicitly add name fields to the form
    first_name = forms.CharField(max_length=150, required=True, label='First Name')
    last_name = forms.CharField(max_length=150, required=True, label='Last Name')

    class Meta:
        model = User
        # CRITICAL: Remove 'username'
        fields = ['first_name', 'last_name', 'email'] # Username is now implicitly the email


class UserProfileUpdateForm(forms.ModelForm):
    """Form for updating custom UserProfile details."""

    college_name = forms.CharField(max_length=255, required=False,
                                   widget=forms.TextInput(attrs={'placeholder': 'Your college name'}))

    profile_icon = forms.FileField(label='Profile Icon', required=False)

    # CRITICAL: Add the phone number field from the UserProfile model
    phone_number = forms.CharField(max_length=15, required=False, label='Mobile Number')

    class Meta:
        model = UserProfile
        # Add 'phone_number' to the fields list
        fields = ['college_name', 'phone_number', 'profile_icon']


# main_app/forms.py

# ... (ensure User is imported: from django.contrib.auth.models import User)

class MandatoryProfileForm(forms.ModelForm):
    """Form for collecting mandatory profile data using AJAX autocomplete for college."""

    # NEW: Add First Name and Last Name fields for users (especially social) who might not have set them
    first_name = forms.CharField(max_length=150, required=True, label='First Name')
    last_name = forms.CharField(max_length=150, required=True, label='Last Name')

    # CRITICAL CHANGE: Change College Name to a simple CharField for AJAX input
    # We will validate it in the clean method.
    college_name = forms.CharField(max_length=500, required=True, label='College Name')

    # Phone number remains mandatory
    phone_number = forms.CharField(max_length=15, required=True, label='Mobile Number')

    # Profile Icon is now OPTIONAL
    profile_icon = forms.FileField(label='Profile Icon (Optional)', required=False)

    class Meta:
        model = UserProfile
        # We only use fields from UserProfile model that are NOT overridden above
        fields = ('phone_number', 'profile_icon')

    # --- New Cleaning Method for College Name ---
    def clean_college_name(self):
        """
        Validates that the college name entered by the user actually exists
        in the database after the AJAX search helps them find it.
        """
        college_name = self.cleaned_data.get('college_name')

        if not college_name:
            # Should be caught by required=True, but safe to check
            raise ValidationError("College Name is required.")

        try:
            # Look up the college name (case-insensitive)
            college = College.objects.get(name__iexact=college_name)
            # Store the college object for use in the save method
            self._selected_college = college
        except College.DoesNotExist:
            raise ValidationError("Please select a valid college name from the suggestions.")

        return college_name

    # --- End New Cleaning Method ---

    def __init__(self, *args, **kwargs):
        # 1. Pop the User instance (if available)
        user_instance = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # 2. Pre-fill name fields from the User instance
        if user_instance:
            self.fields['first_name'].initial = user_instance.first_name
            self.fields['last_name'].initial = user_instance.last_name

        # CRITICAL: Add the HTML 'list' attribute for the datalist hook
        self.fields['college_name'].widget.attrs.update({
            'placeholder': 'Start typing your college name...',
            'list': 'college-suggestions',  # Hook for the JavaScript datalist
            'autocomplete': 'off',
            'id': 'id_college_name'  # Ensure a consistent ID for JS targeting
        })

    def save(self, commit=True):
        profile = super().save(commit=False)

        # CRITICAL: Manually update the linked User instance before saving the profile
        user = profile.user
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.save()  # Save the User model updates

        # CRITICAL: Update the UserProfile's college_name field from the validated object
        if hasattr(self, '_selected_college'):
            profile.college_name = self._selected_college.name

        if commit:
            profile.save()  # Save the UserProfile model updates
        return profile


# main_app/forms.py (Add to the imports section at the top)
from django.forms import inlineformset_factory


# (You may need to add this import if it's missing)

# ... (Add these new classes at the end of the file) ...

class AptitudeTestForm(forms.ModelForm):
    """Form for setting the time limit and test date."""

    # Use DateTimeInput for a better user experience for date_time
    test_start_date_time = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        label='Test Start Date and Time'
    )

    class Meta:
        model = AptitudeTest
        # We only let the user set these two fields. The 'event' field is set in the view.
        fields = ['time_limit_minutes', 'test_start_date_time']

        widgets = {
            'time_limit_minutes': forms.NumberInput(attrs={'min': 1, 'max': 180, 'placeholder': 'e.g., 60 (minutes)'}),
        }


class AptitudeQuestionForm(forms.ModelForm):
    """Form for a single MCQ question and its options/answer."""

    class Meta:
        model = AptitudeQuestion
        fields = [
            'question_text', 'option_a', 'option_b', 'option_c', 'option_d',
            'correct_answer', 'points'
        ]

        widgets = {
            'question_text': forms.Textarea(attrs={'rows': 2}),
            'points': forms.NumberInput(attrs={'min': 1, 'max': 10}),
        }


# CRITICAL: Create the FormSet for multiple questions
# We use AptitudeQuestion model, linked by ForeignKey 'test' in the AptitudeQuestion model.
AptitudeQuestionFormSet = inlineformset_factory(
    AptitudeTest,  # Parent model (AptitudeTest)
    AptitudeQuestion,  # Child model (AptitudeQuestion)
    form=AptitudeQuestionForm,
    extra=1,  # Start with one empty form
    can_delete=True,
    # This is the max number of questions the user can enter
    max_num=50
)



# In main_app/forms.py (Add the following two classes)

class VideoSubmissionForm(forms.ModelForm):
    """Form for uploading a video file for screening."""
    class Meta:
        model = VideoScreeningSubmission
        # We only let the user choose the file. 'user' and 'event' are set in the view.
        fields = ['video_file']

class PhotoSubmissionForm(forms.ModelForm):
    """Form for uploading a photo file for screening."""
    class Meta:
        model = PhotoScreeningSubmission
        # We only let the user choose the file. 'user' and 'event' are set in the view.
        fields = ['photo_file']