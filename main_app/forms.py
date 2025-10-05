# main_app/forms.py

from django import forms
from django.contrib.auth.models import User
from django.forms import ClearableFileInput
from django.core.exceptions import ValidationError

from .models import UserProfile, Post, Event, EventApplicationDetails, College


class MultiFileInput(ClearableFileInput):
    def __init__(self, attrs=None):
        super().__init__(attrs)
        self.attrs['multiple'] = 'multiple'


# main_app/forms.py

class UserRegistrationForm(forms.ModelForm):
    # No changes to the fields visible to the user: email, password, name

    # Password confirmation field
    password_confirm = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)

    class Meta:
        model = User
        # Fields: email, password, first_name, last_name
        fields = ['email', 'password', 'first_name', 'last_name']
        widgets = {
            'password': forms.PasswordInput(),
        }

    # ... (Keep the clean_email, clean_password_confirm, and save methods as they are correct)

    # --- NEW: Method to enforce email as username ---
    def clean_email(self):
        email = self.cleaned_data['email']

        # Check if email is already taken (Django's default check still runs, but this is a good custom safeguard)
        if User.objects.filter(username=email).exists():
            raise ValidationError("A user with that email already exists.")

        # Crucially, set the username field to the email address
        self.cleaned_data['username'] = email
        return email

    def clean_password_confirm(self):
        password = self.cleaned_data.get('password')
        password_confirm = self.cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            raise ValidationError("Passwords do not match.")
        return password_confirm

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])

        # Ensure username is set to email before saving (redundant but safe)
        if 'username' in self.cleaned_data:
            user.username = self.cleaned_data['username']

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
            'show_phone_number_on_query'
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
    """Form for updating core Django User details (username, email)."""
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email']


class UserProfileUpdateForm(forms.ModelForm):
    """Form for updating custom UserProfile details."""

    # Using CharField for college_name as it's a simple text field in UserProfile model
    college_name = forms.CharField(max_length=255, required=False,
                                   widget=forms.TextInput(attrs={'placeholder': 'Your college name'}))

    # We use FileField for the profile icon since you used it in UserRegistrationForm
    profile_icon = forms.FileField(label='Profile Icon', required=False)

    class Meta:
        model = UserProfile
        # We only allow changing college_name and profile_icon
        fields = ['college_name', 'profile_icon']


# main_app/forms.py

# ... (ensure User is imported: from django.contrib.auth.models import User)

class MandatoryProfileForm(forms.ModelForm):
    """Form for collecting mandatory phone number, college name, and optional profile icon."""

    # NEW: Add First Name and Last Name fields for users (especially social) who might not have set them
    first_name = forms.CharField(max_length=150, required=True, label='First Name')
    last_name = forms.CharField(max_length=150, required=True, label='Last Name')

    # College Name remains mandatory (ModelChoiceField confirmed in Step 2 of previous convo)
    college_name = forms.ModelChoiceField(
        queryset=College.objects.all().order_by('name'),
        to_field_name='name',
        label='College Name',
        required=True  # Mandatory
    )

    # Phone number remains mandatory
    phone_number = forms.CharField(max_length=15, required=True, label='Mobile Number')

    # Profile Icon is now OPTIONAL
    profile_icon = forms.FileField(label='Profile Icon (Optional)', required=False)  # <--- MADE OPTIONAL

    class Meta:
        model = UserProfile
        # Only use fields from UserProfile model
        fields = ('college_name', 'phone_number', 'profile_icon')

        # --- NEW: Custom __init__ and save methods to handle User fields (first_name/last_name) ---

    def __init__(self, *args, **kwargs):
        # 1. Pop the User instance (if available) before calling super()
        user_instance = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # 2. Pre-fill name fields from the User instance
        if user_instance:
            self.fields['first_name'].initial = user_instance.first_name
            self.fields['last_name'].initial = user_instance.last_name

        # 3. Add the User model fields (first_name, last_name) to the form's fields list (non-model fields)
        # Note: We manually add them here since they are not part of UserProfile.Meta.fields

    def save(self, commit=True):
        profile = super().save(commit=False)

        # CRITICAL: Manually update the linked User instance before saving the profile
        user = profile.user
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.save()  # Save the User model updates

        if commit:
            profile.save()  # Save the UserProfile model updates
        return profile