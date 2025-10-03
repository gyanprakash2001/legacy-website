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


class UserRegistrationForm(forms.ModelForm):
    # This field now uses the new College model to get its choices
    college_name = forms.ModelChoiceField(
        queryset=College.objects.all(),
        to_field_name='name',
        label='College Name'
    )
    profile_icon = forms.FileField(label='Profile Icon', required=False)

    # Password confirmation field
    password_confirm = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name']
        widgets = {
            'password': forms.PasswordInput(),
        }

    def clean_password_confirm(self):
        password = self.cleaned_data.get('password')
        password_confirm = self.cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            raise ValidationError("Passwords do not match.")
        return password_confirm

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
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