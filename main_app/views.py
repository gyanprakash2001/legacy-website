import requests
from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from .forms import AptitudeTestForm, AptitudeQuestionFormSet
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout
from django.utils import timezone
from django.contrib import messages
from django.db import IntegrityError
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from django.db.models import Q, F  # Ensure F is imported at the top of your views.py
from .models import (
    Event, Post, UserProfile, MediaFile, EventApplicationDetails, Follow, College,
    EventCategory, EventType, ChatMessage, AptitudeTest, AptitudeQuestion,
    AptitudeTestAttempt, VideoScreeningSubmission, PhotoScreeningSubmission, State
)
from .forms import UserRegistrationForm, PostForm, EventCreationForm, EventApplicationForm, UserUpdateForm, UserProfileUpdateForm, VideoSubmissionForm, PhotoSubmissionForm
from datetime import datetime, timedelta
from django.views.decorators.http import require_POST
from .forms import MandatoryProfileForm
from .models import UserProfile, College
from .models import Event
from .decorators import profile_setup_required
from django.http import HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
import json
from django.conf import settings
from .models import Post, MediaFile # Ensure these are imported from .models
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import re









def index(request):
    return render(request, 'main_app/index.html')



def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'main_app/login.html', {'form': form})


def logout_view(request):
    # Log the user out of the Django session
    logout(request)

    # Add a success message to display on the next page (the login page)
    messages.success(request, 'You have successfully logged out.')

    # Redirect to the login page
    return redirect('login')


@login_required
def create_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            for uploaded_file in request.FILES.getlist('media_files'):
                file_type = 'video' if uploaded_file.content_type.startswith('video') else 'image'
                MediaFile.objects.create(post=post, file=uploaded_file, file_type=file_type)
            return redirect('dashboard')
    else:
        form = PostForm()
    return render(request, 'main_app/create_post.html', {'form': form})




@login_required
@profile_setup_required  # This enforces the redirect to the setup page if profile is incomplete
def dashboard(request):
    user = request.user

    # NOTE: The manual profile check and modal instantiation has been removed.
    # We now assume the profile is complete if this function runs.

    # 1. Get the list of college names the user is following via the Follow model
    followed_college_names = list(Follow.objects.filter(follower=user).values_list('college_name', flat=True))

    # 2. Get the user's own college name (This ensures posts from their college are always seen)
    # We must assume user_profile exists because of the @profile_setup_required decorator
    user_college_name = user.userprofile.college_name

    # Add the user's own college to the filter list if it's not already there (it might be followed explicitly)
    if user_college_name and user_college_name not in followed_college_names:
        followed_college_names.append(user_college_name)

    # 3. Filter Posts: Show followed posts plus recent general activity (CLEANED LOGIC)

    # Base query: Posts where the author's college name is IN the list of followed colleges
    followed_posts_query = Post.objects.select_related('author__userprofile').prefetch_related(
        'media_files').filter(
        Q(author__userprofile__college_name__in=followed_college_names)
    )

    # Get a few recent posts that are NOT from the followed list
    general_posts_query = Post.objects.select_related('author__userprofile').prefetch_related(
        'media_files').exclude(
        Q(author__userprofile__college_name__in=followed_college_names)
    ).order_by('-created_at')[:10]  # Limit to 10 recent general posts

    # Combine the query results.
    posts_list = list(followed_posts_query) + list(general_posts_query)

    # Sort the final combined list by creation date in reverse order
    posts_list.sort(key=lambda post: post.created_at, reverse=True)

    # FIX: Add select_related('organizer') to fetch the organizer's User object (which contains the email)
    upcoming_events = Event.objects.filter(date_time__gte=timezone.now()).select_related('event_type',
                                                                                         'organizer').order_by(
        'date_time')

    # --- Sidebar Data ---
    # Fetch the suggested colleges needed for the right sidebar
    try:
        suggested_colleges = list(College.objects.all().order_by('?')[:3])
    except:
        suggested_colleges = []

    # Fetch all categories and their related event types for the filter dropdowns
    event_categories = EventCategory.objects.all().order_by('name')
    categories_with_types = []
    for category in event_categories:
        types = EventType.objects.filter(category=category).order_by('name')
        categories_with_types.append({
            'category': category,
            'types': types,
        })
    # --- END Sidebar Data ---

    # Ensure posts_list is passed in the context
    context = {
        'posts_list': posts_list,
        'upcoming_events': upcoming_events,
        'suggested_colleges': suggested_colleges,
        'categories_with_types': categories_with_types,

        # The NEW CONTEXT for the modal is removed, as it's no longer needed here.
    }

    return render(request, 'main_app/dashboard.html', context)


@login_required
@profile_setup_required
def create_event(request):
    event_link = None  # Not strictly necessary, but good to keep if used later
    initial_data = {}

    # --- 1. DEFINE CATEGORIES (MUST BE DEFINED EARLY) ---
    event_categories = EventCategory.objects.all().order_by('name')
    categories_with_types = []
    for category in event_categories:
        types = EventType.objects.filter(category=category).order_by('name')
        categories_with_types.append({
            'category': category,
            'types': types,
        })
    # --- END CATEGORIES DEFINITION ---

    # --- 2. STATE AUTOFILL LOGIC (Robust String Extraction) ---
    # Wrap this in try/except to prevent an error from blocking the function return
    user_college_state = None
    try:
        user_profile = request.user.userprofile
        user_college_name_str = user_profile.college_name

        separator = ' - '
        if separator in user_college_name_str:
            state_parts = user_college_name_str.rsplit(separator, 1)
            user_college_state = state_parts[-1].strip()

    except UserProfile.DoesNotExist:
        pass
    except Exception:
        # Pass on any exception here to allow the rest of the view to execute
        pass

    if user_college_state:
        initial_data['state'] = user_college_state

    # --- 3. HANDLE REQUEST METHOD ---
    if request.method == 'POST':
        form = EventCreationForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.save()  # Save the event

            # ... (Keep existing screening redirection logic) ...
            selected_screening = event.screening_type

            if selected_screening != 'none':
                messages.info(request,
                              f'Event saved! Now, please finalize your {selected_screening.title()} Screening setup.')
                return redirect('screening_setup', event_link_key=event.event_link_key,
                                screening_type=selected_screening)

            messages.success(request, 'Event created successfully!')
            return redirect('event_log')

            # If POST is invalid, execution falls through to the final return,
        # ensuring the form is re-rendered with errors.

    else:
        # GET Request: Initialize form with autofilled data
        form = EventCreationForm(initial=initial_data)

    # 4. FINAL RETURN: This must be hit on both GET requests and failed POST requests.
    return render(request, 'main_app/create_event.html', {'form': form, 'categories_with_types': categories_with_types})


def get_events(request):
    events = Event.objects.all()
    event_list = []
    for event in events:
        formatted_date = event.date_time.strftime('%Y-%m-%d')
        event_list.append({
            'date': formatted_date,
            'title': event.event_name,
            'summary': f"{event.event_name}, Location: {event.location}, Fees: {event.registration_fees}",
        })
    return JsonResponse(event_list, safe=False)


@login_required
def apply_for_event(request, event_link_key):
    event = get_object_or_404(Event, event_link_key=event_link_key)

    if request.method == 'POST':
        form = EventApplicationForm(request.POST)
        if form.is_valid():
            if EventApplicationDetails.objects.filter(user=request.user, event=event).exists():
                messages.error(request, 'You have already applied for this event.')
            else:
                application = form.save(commit=False)
                application.user = request.user
                application.event = event
                application.save()
                messages.success(request, f'You have successfully applied for {event.event_name}!')

                # ⭐ NEW REDIRECTION CHECK AFTER SUCCESSFUL APPLICATION ⭐
                if event.screening_type == 'aptitude':
                    # Ensure the test is configured before redirecting
                    if hasattr(event, 'aptitude_test'):
                        return redirect('test_start_page', event_link_key=event.event_link_key)

                elif event.screening_type == 'video':
                    # Redirect to media upload page for video submission
                    return redirect('media_upload_page', event_link_key=event.event_link_key, media_type='video')

                elif event.screening_type == 'photo':
                    # Redirect to media upload page for photo submission
                    return redirect('media_upload_page', event_link_key=event.event_link_key, media_type='photo')

                # Default redirect if screening_type is 'none'
                return redirect('dashboard')
            return redirect('dashboard')

    else:  # GET Request
        initial_data = {}
        try:
            user_profile = request.user.userprofile
            initial_data['name'] = request.user.username
            initial_data['email_id'] = request.user.email
            initial_data['college_name'] = user_profile.college_name
            if hasattr(user_profile, 'whatsapp_number'):
                initial_data['whatsapp_number'] = user_profile.whatsapp_number
        except UserProfile.DoesNotExist:
            pass

        # ⭐ CHECK IF APPLICATION ALREADY EXISTS AND REDIRECT TO SCREENING PAGE ⭐
        if EventApplicationDetails.objects.filter(user=request.user, event=event).exists():
            messages.info(request, "You've already applied. Checking required screening status...")

            if event.screening_type == 'aptitude' and hasattr(event, 'aptitude_test'):
                return redirect('test_start_page', event_link_key=event.event_link_key)

            elif event.screening_type == 'video':
                return redirect('media_upload_page', event_link_key=event.event_link_key, media_type='video')

            elif event.screening_type == 'photo':
                return redirect('media_upload_page', event_link_key=event.event_link_key, media_type='photo')

            # If application exists but screening is 'none', or media/test is done, go to dashboard.
            messages.info(request, "Application confirmed. See you at the event!")
            return redirect('dashboard')

        form = EventApplicationForm(initial=initial_data)

    context = {
        'form': form,
        'event': event
    }
    return render(request, 'main_app/apply_for_event.html', context)

def event_details(request, event_title):
    event = Event.objects.filter(event_name=event_title).first()

    if event:
        apply_form = EventApplicationForm()
        return render(request, 'main_app/event_details.html', {'event': event, 'apply_form': apply_form})
    else:
        raise Http404("Event does not exist")


@login_required
def my_community_view(request):
    user = request.user
    if hasattr(user, 'userprofile'):
        user_college = user.userprofile.college_name

        community_posts = Post.objects.filter(author__userprofile__college_name=user_college).order_by('-created_at')

        # New code to fetch upcoming events and suggested colleges
        upcoming_events = Event.objects.filter(date_time__gte=timezone.now()).select_related('event_type',
                                                                                             'organizer').order_by(
            'date_time')
        suggested_colleges = list(College.objects.all().order_by('?')[:3])

        # Fetch categories/types for event filters (likely needed for the community view's sidebar too)
        event_categories = EventCategory.objects.all().order_by('name')
        categories_with_types = []
        for category in event_categories:
            types = EventType.objects.filter(category=category).order_by('name')
            categories_with_types.append({
                'category': category,
                'types': types,
            })

        context = {
            'posts_list': community_posts,
            'community_page': True,
            'upcoming_events': upcoming_events,
            'suggested_colleges': suggested_colleges,
            'categories_with_types': categories_with_types,
        }
        return render(request, 'main_app/dashboard.html', context)
    else:
        # Handle case where user does not have a UserProfile
        context = {
            'posts_list': [],
            'community_page': True,
            'upcoming_events': [],
            'suggested_colleges': [],
            'categories_with_types': [],
        }
        return render(request, 'main_app/dashboard.html', context)


@login_required
def event_log_view(request):
    # Fetch all events where the current user is the organizer
    my_events = Event.objects.filter(organizer=request.user).order_by('-date_time')

    context = {
        'my_events': my_events
    }
    return render(request, 'main_app/event_log.html', context)


@login_required
def my_applications_view(request):
    """
    Displays all events the current user has applied for.
    The application details are stored in the EventApplicationDetails model.
    """
    user_applications = EventApplicationDetails.objects.filter(user=request.user).select_related(
        'event__event_type').order_by('-applied_at')
    # Note: We are using a separate application_date field that would need to be added
    # to your EventApplicationDetails model for correct sorting if it's not there.
    # For now, we sort by event date.

    # If the EventApplicationDetails model doesn't have an application_date:
    # user_applications = EventApplicationDetails.objects.filter(user=request.user).select_related('event__event_type').order_by('-event__date_time')

    context = {
        'user_applications': user_applications,
        'page_title': 'My Applications Log',
        'is_applications_page': True,  # Optional flag for template customization
    }

    # We will use a new dedicated template for this page
    return render(request, 'main_app/my_applications_log.html', context)


# ... (inside views.py) ...

@login_required
def registrations_view(request, event_id):
    # Get the specific event or return a 404 error
    event = get_object_or_404(Event, id=event_id, organizer=request.user)

    # Get all applications for this specific event, ordered by name
    registrations = EventApplicationDetails.objects.filter(event=event).order_by('name')

    # ⭐ NEW LOGIC: Check for Screening Type and Fetch Submissions ⭐
    screening_type = event.screening_type
    applicant_submissions = {}

    if screening_type == 'aptitude':
        # Fetch scores if aptitude test is enabled and set up
        if hasattr(event, 'aptitude_test'):
            aptitude_test = event.aptitude_test
            # Fetch all attempts for this test, linking to the User for easy lookup
            attempts = aptitude_test.attempts.select_related('user')

            # Map scores to the user ID for quick retrieval in the template
            for attempt in attempts:
                # Use user_id as the key, as application details also link to user
                applicant_submissions[attempt.user_id] = {
                    'score': attempt.score,
                    'time_taken_seconds': attempt.time_taken_seconds
                }

    elif screening_type == 'video':
        # Fetch Video Submissions (One-to-One from User model)
        submissions = VideoScreeningSubmission.objects.filter(event=event).select_related('user')
        for sub in submissions:
            applicant_submissions[sub.user.pk] = {'media_url': sub.video_file.url}

    elif screening_type == 'photo':
        # Fetch Photo Submissions (One-to-One from User model)
        submissions = PhotoScreeningSubmission.objects.filter(event=event).select_related('user')
        for sub in submissions:
            applicant_submissions[sub.user.pk] = {'media_url': sub.photo_file.url}

    context = {
        'event': event,
        'registrations': registrations,
        'screening_type': screening_type,  # New flag for template
        'applicant_submissions': applicant_submissions,  # New data for template
    }

    return render(request, 'main_app/registrations.html', context)



def college_autocomplete(request):
    """
    Provides a list of college names for an autocomplete field.
    """
    query = request.GET.get('q', '')
    colleges = College.objects.filter(name__icontains=query)[:10]  # Limit to 10 results
    results = [{'id': college.id, 'name': college.name} for college in colleges]
    return JsonResponse(results, safe=False)



@login_required
def filter_events_api(request):
    # Base Query: Start with all upcoming events
    events_queryset = Event.objects.filter(date_time__gte=timezone.now()).select_related('event_type').order_by(
        'date_time')

    # 1. Get Filters from GET request (REMAINS THE SAME)
    event_type_id = request.GET.get('event_type', '')
    fees_filter = request.GET.get('fees', '')
    my_college_only = request.GET.get('my_college_only', 'false') == 'true'
    applied_filter = request.GET.get('applied_filter', 'false') == 'true'

    # --- Start building complex QuerySet filters with Q objects ---
    filters = Q()

    # 2. Filter by Event Type
    if event_type_id:
        filters &= Q(event_type__id=event_type_id)

    # 3. Filter by Fees
    if fees_filter == 'free':
        filters &= Q(registration_fees__isnull=True)
    elif fees_filter == 'paid':
        filters &= Q(registration_fees__isnull=False)

    # 4. Filter by My College Only (ROBUST Q LOGIC)
    if my_college_only:
        try:
            user_college = request.user.userprofile.college_name
            if user_college:
                filters &= Q(organizer__userprofile__college_name=user_college)
            else:
                # If user's college is null, the result should be an empty set
                events_queryset = events_queryset.none()

        except UserProfile.DoesNotExist:
            events_queryset = events_queryset.none()

    # 5. Filter by Applied Events
    if applied_filter:
        applied_event_ids = EventApplicationDetails.objects.filter(user=request.user).values_list('event_id', flat=True)
        filters &= Q(id__in=applied_event_ids)

    # --- Apply all filters to the QuerySet ---
    if filters:
        events_queryset = events_queryset.filter(filters)

    # ... (Rest of the function remains the same)

    # Convert QuerySet to list of dictionaries for easier JSON serialization
    # ... (REMAINS THE SAME)

    # Convert QuerySet to list of dictionaries for easier JSON serialization
    upcoming_events = list(events_queryset.values(
        'id', 'event_name', 'event_type_id', 'location', 'date_time',
        'registration_fees', 'event_link_key', 'organizer__email', 'phone_number', 'show_phone_number_on_query',
        event_type_name=F('event_type__name')
    ))

    # Manually attach the event type name to the events list
    for event_data in upcoming_events:
        event_data['event_type'] = {'name': event_data.pop('event_type_name')}

    # Render the filtered events using a partial template
    html_content = render_to_string('main_app/includes/event_list.html', {'upcoming_events': upcoming_events},
                                    request=request)

    return JsonResponse({'html': html_content})


# Locate the calendar_events_api function and replace its contents.

@login_required
def calendar_events_api(request):
    events_queryset = Event.objects.filter(date_time__gte=timezone.now()).select_related('event_type').order_by(
        'date_time')

    # --- 1. Get Filters from GET request ---
    event_type_id = request.GET.get('event_type', '')
    fees_filter = request.GET.get('fees', '')
    my_college_only = request.GET.get('my_college_only', 'false') == 'true'
    applied_filter = request.GET.get('applied_filter', 'false') == 'true'

    # NEW FILTERS: Get College and State names
    college_name_filter = request.GET.get('college_name', '').strip()
    state_filter = request.GET.get('state', '').strip()

    # --- 2. Apply Filters to Queryset ---
    if event_type_id:
        events_queryset = events_queryset.filter(event_type__id=event_type_id)
    if fees_filter == 'free':
        events_queryset = events_queryset.filter(registration_fees__isnull=True)
    elif fees_filter == 'paid':
        events_queryset = events_queryset.filter(registration_fees__isnull=False)

    if my_college_only:
        try:
            user_college = request.user.userprofile.college_name
            events_queryset = events_queryset.filter(organizer__userprofile__college_name=user_college)
        except UserProfile.DoesNotExist:
            events_queryset = events_queryset.none()

    if applied_filter:
        applied_event_ids = EventApplicationDetails.objects.filter(user=request.user).values_list('event_id', flat=True)
        events_queryset = events_queryset.filter(id__in=applied_event_ids)

    # NEW FILTER LOGIC: Apply College and State Filters
    if college_name_filter:
        # Filter by organizer's college name (case-insensitive search)
        events_queryset = events_queryset.filter(organizer__userprofile__college_name__icontains=college_name_filter)

    if state_filter:
        # Filter by the location field in the Event model (assuming state is part of location/city/state)
        events_queryset = events_queryset.filter(location__icontains=state_filter)

    # --- 3. Return Event Details Mapped by Date ---
    event_data_by_date = {}

    for event in events_queryset.values(
            'id', 'event_name', 'date_time', 'event_link_key', 'location', 'organizer__email',
            event_type_name=F('event_type__name')
    ):
        date_str = event['date_time'].strftime('%Y-%m-%d')

        if date_str not in event_data_by_date:
            event_data_by_date[date_str] = []

        event_data_by_date[date_str].append({
            'name': event['event_name'],
            'link_key': str(event['event_link_key']),
            'location': event['location'],
            'type_name': event['event_type_name'],
            'organizer_email': event['organizer__email'],
            'date_time': event['date_time'].strftime('%Y-%m-%d %H:%M'),
        })

    return JsonResponse({'events_by_date': event_data_by_date}, safe=False)

@login_required
def daily_events_view(request, date_str):
    # This view fetches all events for a specific day after a calendar click

    try:
        # 1. Parse the date string (YYYY-MM-DD)
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return redirect('dashboard')  # Redirect on bad date format

    # Base Query: Filter by the target date
    events_queryset = Event.objects.filter(date_time__date=target_date).select_related('event_type').order_by(
        'date_time')

    # --- Pass data to template ---
    context = {
        'upcoming_events': events_queryset,
        'page_title': f'Events on {target_date.strftime("%B %d, %Y")}'
    }

    # We will reuse the dashboard.html structure for the clean layout
    return render(request, 'main_app/dashboard.html', context)


@login_required
@require_POST
def toggle_follow_college(request):
    college_name = request.POST.get('college_name')
    action = request.POST.get('action')
    user = request.user

    # 1. Ensure the college exists
    try:
        # Assuming College model has a 'name' field
        college_obj = College.objects.get(name=college_name)
    except College.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'College not found'}, status=404)

    # 2. Implement Follow/Unfollow Logic
    if action == 'follow':
        # Create the Follow object only if it doesn't already exist
        # The Follow model takes the User object and the College name (string)
        try:
            Follow.objects.create(follower=user, college_name=college_name)
            status = 'followed'
        except IntegrityError:
            # Already following
            status = 'followed'

    elif action == 'unfollow':
        # Find and delete the Follow object
        Follow.objects.filter(follower=user, college_name=college_name).delete()
        status = 'unfollowed'

    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid action'}, status=400)

    # 3. Return a JSON response
    return JsonResponse({'status': status})


@login_required
def college_community_view(request, college_name):
    """View for a specific college's community page."""

    # 1. IMPROVED LOGIC to strip the location/place for the page heading
    clean_name = college_name.strip()
    separators = [' - ', ', ', ' - ', ' -']  # Check for common separators

    for sep in separators:
        if sep in clean_name:
            # Split by the separator and take the first part
            clean_name = clean_name.split(sep)[0].strip()
            # Stop checking once a separator is found and split
            break

    # The clean_name variable now holds the college name without the location suffix

    # 2. Filter posts to show only those from the specific college (rest remains the same)
    posts_list = Post.objects.select_related('author__userprofile').prefetch_related('media_files').filter(
        author__userprofile__college_name=college_name
    ).order_by('-created_at')

    # 3. Fetch data needed for the sidebar (similar to the dashboard view)
    upcoming_events = Event.objects.filter(date_time__gte=timezone.now()).select_related('event_type',
                                                                                         'organizer').order_by(
        'date_time')
    suggested_colleges = list(College.objects.all().order_by('?')[:3])
    event_categories = EventCategory.objects.all().order_by('name')
    categories_with_types = []
    for category in event_categories:
        types = EventType.objects.filter(category=category).order_by('name')
        categories_with_types.append({
            'category': category,
            'types': types,
        })

    context = {
        'posts_list': posts_list,
        'page_heading': f"{clean_name} - Community",  # <-- New variable for the heading text
        'is_college_community': True,  # <-- New specific flag for template
        # 'community_page_name' has been removed/renamed to 'page_heading' for clarity
        'community_page': True,
        'upcoming_events': upcoming_events,
        'suggested_colleges': suggested_colleges,
        'categories_with_types': categories_with_types,
    }

    return render(request, 'main_app/dashboard.html', context)


def state_autocomplete(request):
    """
    Provides a list of unique state names for autocomplete.
    It fetches clean state names that match the query.
    """
    query = request.GET.get('q', '').strip()

    # CRITICAL FIX: Directly fetch the distinct State names from the database,
    # ensuring they start with the user's query (query__istartswith).

    # This filter directly searches the cleaned State field and ignores messy text.
    unique_states_raw = College.objects.filter(
        state__istartswith=query  # Use istartswith for accurate, clean matching
    ).exclude(
        state__isnull=True
    ).exclude(
        state=''
    ).values_list('state', flat=True).distinct()

    # 2. Server-Side Cleaning (Just stripping and finalizing)
    cleaned_and_filtered_states = set()

    for state in unique_states_raw:
        final_state_name = state.strip()

        # Heuristic checks (remove numbers, short names)
        if not any(char.isdigit() for char in final_state_name) and len(final_state_name) > 3:
            cleaned_and_filtered_states.add(final_state_name)

    # 3. Limit and format the results
    final_results = sorted(list(cleaned_and_filtered_states))[:10]
    results = [{'state_name': state} for state in final_results]

    return JsonResponse(results, safe=False)


# --- NEW PROFILE VIEW ---

@login_required
def profile_view(request):
    """
    Handles displaying and updating the core User and custom UserProfile data.
    """
    # This ensures the user has a UserProfile entry (critical for the system)
    try:
        user_profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        messages.error(request, "User profile not found. Please contact support.")
        return redirect('dashboard')

    if request.method == 'POST':
        # Instantiating forms with request.POST data and existing instances
        # request.FILES is needed to handle profile icon uploads
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = UserProfileUpdateForm(request.POST, request.FILES, instance=user_profile)

        if user_form.is_valid() and profile_form.is_valid():
            # Save core User details (username, email)
            user_form.save()

            # Save UserProfile details (college_name, profile_icon)
            # The profile_form handles the file upload automatically
            profile_form.save()

            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('profile')  # Redirects back to the profile page
        else:
            messages.error(request, 'There was an error updating your profile. Please check the fields.')

    else:
        # GET request: pre-fill forms with current user data
        user_form = UserUpdateForm(instance=request.user)
        profile_form = UserProfileUpdateForm(instance=user_profile)

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'current_user_profile': user_profile,  # Pass profile object for viewing
        'is_profile_page': True  # Flag for template navigation/styling
    }

    return render(request, 'main_app/profile.html', context)




# In main_app/views.py

# In main_app/views.py (This must replace the entire function body)

@login_required
def mandatory_profile_setup_view(request):
    user = request.user

    # 1. Get the profile instance and check for existence
    try:
        user_profile = user.userprofile
    except UserProfile.DoesNotExist:
        messages.error(request, "User profile missing.")
        return redirect('dashboard')

    # 2. Safety check: If setup is ALREADY complete, send them to the dashboard.
    if user_profile.setup_complete:
        return redirect('dashboard')

    if request.method == 'POST':
        # Handle POST submission (user clicks 'Complete Setup')
        form = MandatoryProfileForm(request.POST, request.FILES, instance=user_profile, user=user)

        if form.is_valid():
            # Success path: Mark complete and redirect
            profile = form.save(commit=False)
            profile.setup_complete = True
            profile.save()

            messages.success(request, 'Profile setup complete! Welcome to the dashboard.')
            return redirect('dashboard')
        else:
            # Failure path: Errors will be shown on the form when rendered below
            messages.error(request, 'There were errors in your profile data. Please check and try again.')
            # Do NOT redirect. Fall through to the rendering step.

    # 💥 CRITICAL: This is the rendering path for both GET and failed POST submissions.
    else:
        # GET request (initial page load)
        form = MandatoryProfileForm(instance=user_profile, user=user)

    # 3. RENDER THE DEDICATED TEMPLATE
    context = {
        'form': form,
        'page_title': 'Complete Profile Setup'
    }

    # This is the final step that renders the dedicated page, breaking the redirect loop.
    return render(request, 'main_app/mandatory_profile_setup.html', context)
# In main_app/views.py (within the register_view function)


def register_view(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)

        if form.is_valid():
            try:
                # 1. Save the User. (The form handles username=email and password hashing)
                user = form.save()

                # 2. UserProfile creation is handled by the post_save signal in models.py.
                # If we trust the signal, we don't need the explicit UserProfile.objects.create().
                # Let's trust the signal for a clean view.

                # 3. Log In and Redirect (CRITICAL SUCCESS PATH)
                login(request, user)

                messages.success(request, 'Account created successfully! Please complete your profile.')

                # Success: Redirect to the next step
                return redirect('dashboard')

            except Exception as e:
                # This catches any UNEXPECTED errors during the save or login process.
                # The "user exists" check is now handled by the clean_email in forms.py.
                messages.error(request, f'Registration failed: An unexpected error occurred. {e}')
                # Fall through to re-render the form with errors
    else:
        # GET request
        form = UserRegistrationForm()

    # Re-render the form on GET or POST failure
    return render(request, 'main_app/register_form.html', {'form': form})





def register_choice_view(request):
    """
    Presents the user with a choice between email/password registration
    or social media registration.
    """
    return render(request, 'main_app/register_choice.html')

# ... (then, rename your existing 'register' view to 'email_register_view')


# main_app/views.py (Add the new view at the end)

from django.shortcuts import render, redirect  # Ensure these are imported


def social_login_view(request):
    """
    Handles successful social login (after external authentication)
    and forces the user to the mandatory setup flow if their profile is incomplete.
    """
    if not request.user.is_authenticated:
        # Should not happen in a real setup, but a safety check
        return redirect('login')

    user = request.user

    # 1. Check if UserProfile exists
    try:
        profile = user.userprofile
    except UserProfile.DoesNotExist:
        # This is a NEW social user. We must create the profile.

        # --- CRITICAL: Create Profile for Social User ---
        UserProfile.objects.create(
            user=user,
            college_name="Not Set",  # Placeholder, collected in mandatory setup
            setup_complete=False,  # Force setup
            # Other fields (phone_number, profile_icon) use defaults/nulls
        )
        messages.info(request, "Welcome! Please complete your profile to access the community.")
        return redirect('dashboard')

    # 2. If profile exists, check if mandatory setup is complete
    if not profile.setup_complete:
        messages.info(request, "Please complete your profile setup.")
        return redirect('dashboard')

    # 3. If setup is complete, send them to the dashboard
    return redirect('dashboard')


# main_app/views.py (Add new placeholder view)

def social_login_start_view(request):
    """
    Simulates the start of the social login process.
    It creates or logs in a test user and redirects to the success handler.
    """
    # 1. Ensure a test user exists or create one.
    try:
        # Use a unique email/username for the test Google user
        test_email = 'google.test.user@example.com'
        test_user = User.objects.get(Q(email=test_email) | Q(username=test_email))
    except User.DoesNotExist:
        # Create a new user if not found (simulating first-time social signup)
        test_user = User.objects.create_user(
            username=test_email,
            email=test_email,
            password='testpassword123',
            first_name='Google',
            last_name='Test'
        )
        test_user.save()

    # 2. Log in the test user
    login(request, test_user)

    # 3. Redirect to the success handler, which will check for the mandatory profile setup.
    return redirect('social_login_success')


def event_detail_view(request, event_link_key):
    """
    Handles displaying the details for a single event.
    """
    # Use the event_link_key (UUID) to fetch the specific Event object
    # Assuming 'event_link_key' is the field name on your Event model
    event = get_object_or_404(Event, event_link_key=event_link_key)

    context = {
        'event': event,
        'page_title': event.event_name  # Dynamically set the title
    }

    # You will need to create the 'main_app/event_detail.html' template
    return render(request, 'main_app/event_detail.html', context)






@csrf_exempt  # This is essential to allow external POST requests from Meta
def instagram_webhook(request):
    # --- 1. HANDLE WEBHOOK VERIFICATION (GET REQUEST) ---
    if request.method == 'GET':
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')

        # Validate the mode and the token against your stored secret
        if mode == 'subscribe' and token == settings.INSTAGRAM_VERIFY_TOKEN:
            # Success: Return the challenge string provided by Meta
            return HttpResponse(challenge, status=200)
        else:
            # Failure: If the token doesn't match, raise 404
            return HttpResponse(status=403)  # Forbidden status for security

    # --- 2. HANDLE REAL-TIME NOTIFICATIONS (POST REQUEST) ---
    if request.method == 'POST':
        try:
            # Decode the incoming JSON payload
            data = json.loads(request.body.decode('utf-8'))

            # 1. Get the Admin User and Token (The key to the kingdom)
            # IMPORTANT: We assume the notification relates to the admin/tester user 'Legacy'
            try:
                # Retrieve the admin user whose profile holds the long-lived token
                admin_user = User.objects.get(username='Legacy')
                access_token = admin_user.userprofile.instagram_access_token
            except (User.DoesNotExist, UserProfile.DoesNotExist):
                # If the user or token is missing, cannot process the webhook
                return HttpResponse('Admin user or token missing.', status=403)

            if not access_token:
                return HttpResponse('No access token found.', status=403)

            # 2. Loop through entries and check for 'media' changes
            for entry in data.get('entry', []):
                for change in entry.get('changes', []):
                    # Check if the notification is about new media/post
                    if change.get('field') == 'media':

                        media_id = change.get('value', {}).get('media_id')

                        if media_id:
                            # --- 3. Make the API Call to Fetch FULL Post Data ---

                            # Fields to fetch: caption, media_url, media_type, permalink, timestamp
                            fields = 'caption,media_url,media_type,permalink,timestamp'

                            api_url = f'https://graph.facebook.com/v19.0/{media_id}'

                            response = requests.get(
                                api_url,
                                params={'fields': fields, 'access_token': access_token}
                            )

                            post_data = response.json()

                            # --- 4. Create Post in Django DB ---
                            if post_data.get('id'):

                                # Use media_id as the content source for unique identification
                                post = Post.objects.create(
                                    author=admin_user,
                                    content=post_data.get('caption', 'New post from Instagram.'),
                                    source_link=post_data.get('permalink', ''),
                                )

                                # --- 5. Save the Media File to Cloudinary/Filesystem ---
                                media_url = post_data.get('media_url')
                                media_type = post_data.get('media_type', 'IMAGE')

                                if media_url:
                                    is_video = (media_type == 'VIDEO' or media_type == 'REELS')
                                    # NOTE: The save_media_from_url helper function must be defined
                                    # at the top of your views.py file for this line to work.
                                    # It handles downloading the image/video and saving it to your MediaFile model.
                                    save_media_from_url(post, media_url, is_video=is_video)

            # Meta requires a 200 status code response to confirm receipt.
            return HttpResponse('EVENT_RECEIVED', status=200)

        except json.JSONDecodeError:
            return HttpResponse('Invalid JSON format', status=400)

        except Exception as e:
            # Log general processing errors
            print(f"WEBHOOK PROCESSING ERROR: {e}")
            return HttpResponse(status=500)

    # Return 405 Method Not Allowed for any other method
    return HttpResponse(status=405)





@login_required
def instagram_auth_start(request):
    import json
    from urllib.parse import urlencode

    # 1. JSON payload to trigger the Instagram onboarding channel
    extras_json = json.dumps({"setup": {"channel": "IG_API_ONBOARDING"}})

    params = {
        'client_id': '692028360605970', # Your main Meta App ID
        'redirect_uri': 'https://gyan.pythonanywhere.com/auth/callback/',

        # CRITICAL FIX: Replaced 'instagram_manage_content' with 'instagram_content_publish'
        'scope': 'pages_show_list,instagram_basic,instagram_content_publish',
        'response_type': 'code',

        # Mandatory parameters for the Facebook Login Dialog for Business:
        'display': 'page',
        'extras': extras_json,
        'auth_type': 'reauthenticate',
    }

    # Use the correct Facebook endpoint for Business Login:
    auth_url = f"https://www.facebook.com/dialog/oauth?{urlencode(params)}"

    return redirect(auth_url)


# main_app/views.py

# WARNING: The @login_required decorator must be REMOVED from this function.

# WARNING: Ensure the @login_required decorator is NOT used above this function.

# WARNING: Ensure the @login_required decorator is NOT used above this function.

def instagram_auth_callback(request):
    """
    Receives the authorization code, exchanges it for the Long-Lived Token,
    retrieves the permanent Instagram User ID, and links the tokens to the
    currently authenticated user's profile.
    """
    if not request.user.is_authenticated:
        # Safety check: Redirect if the user is NOT logged in.
        messages.error(request, "Please log in first to link your Instagram account.")
        return redirect('login')

    # 1. Capture the authorization code
    auth_code = request.GET.get('code')
    if not auth_code:
        messages.error(request, "Instagram connection failed: Authorization code missing.")
        return redirect('dashboard')

    # --- API Call 1: Exchange Code for Short-Lived Token ---
    try:
        token_exchange_response = requests.post(
            'https://api.instagram.com/oauth/access_token',
            data={
                'client_id': settings.INSTAGRAM_APP_ID,
                'client_secret': settings.INSTAGRAM_APP_SECRET,
                'grant_type': 'authorization_code',
                # Uses the setting variable (ensures consistency with Meta dashboard)
                'redirect_uri': settings.INSTAGRAM_REDIRECT_URI,
                'code': auth_code
            }
        )
        # Raise exception for bad HTTP status codes (e.g., 400)
        token_exchange_response.raise_for_status()
        token_data = token_exchange_response.json()

        short_token = token_data.get('access_token')

        if not short_token:
            messages.error(request, f"Token exchange failed: {token_data.get('error_message', 'Unknown error.')}")
            return redirect('dashboard')

    except requests.exceptions.RequestException as e:
        messages.error(request, f"API Connection Error (Short Token Exchange): {e}")
        return redirect('dashboard')
    except Exception as e:
        messages.error(request, f"API Response Error (Short Token): {e}")
        return redirect('dashboard')

    # --- API Call 2: Exchange Short-Lived Token for Long-Lived Token (FIXED ENDPOINT) ---
    try:
        long_token_response = requests.get(
            # FIX: Use the FB Graph endpoint for Long-Lived Token exchange
            'https://graph.facebook.com/oauth/access_token',
            params={
                # FIX: Use fb_exchange_token grant type
                'grant_type': 'fb_exchange_token',
                'client_secret': settings.INSTAGRAM_APP_SECRET,
                # FIX: Use the correct parameter name for the token
                'fb_exchange_token': short_token
            }
        )
        long_token_response.raise_for_status()
        long_token_data = long_token_response.json()
        long_token = long_token_data.get('access_token')

        if not long_token:
            messages.error(request,
                           f"Token exchange failed: {long_token_data.get('error', {}).get('message', 'Unknown long token error.')}")
            return redirect('dashboard')

    except requests.exceptions.RequestException as e:
        messages.error(request, f"API Connection Error (Long Token Exchange): {e}")
        return redirect('dashboard')
    except Exception as e:
        messages.error(request, f"API Response Error (Long Token): {e}")
        return redirect('dashboard')

    # --- API Call 3: Get Permanent Instagram User ID (FIX FOR BLANK ID) ---
    try:
        # FIX: Use the FB Graph endpoint to fetch the linked Instagram business account details
        user_id_response = requests.get(
            'https://graph.facebook.com/me',
            params={
                # FIX: Request the nested instagram_business_account object
                'fields': 'id,username,instagram_business_account',
                'access_token': long_token
            }
        )
        user_id_response.raise_for_status()
        user_id_data = user_id_response.json()

        # CRITICAL FIX: Extract the ID from the nested object
        permanent_instagram_user_id = user_id_data.get('instagram_business_account', {}).get('id')

        if not permanent_instagram_user_id:
            messages.error(request,
                           "Failed to retrieve permanent Instagram User ID. Please ensure your IG account is linked to a Facebook Page and is a Business/Creator account.")
            return redirect('dashboard')

    except requests.exceptions.RequestException as e:
        messages.error(request, f"API Connection Error (User ID Fetch): {e}")
        return redirect('dashboard')
    except Exception as e:
        messages.error(request, f"API Response Error (User ID Fetch): {e}")
        return redirect('dashboard')

    # --- 4. Link and Save to CURRENTLY LOGGED-IN USER ---
    try:
        user_profile = request.user.userprofile
        fallback_user_id = permanent_instagram_user_id if permanent_instagram_user_id else token_data.get('user_id')

        user_profile.instagram_access_token = long_token
        user_profile.instagram_user_id = fallback_user_id  # Saves the now-correct ID
        user_profile.save()

        messages.success(request, "Success! Your Instagram Account is now linked and ready to fetch data! 🥳")
        return redirect('dashboard')

    except UserProfile.DoesNotExist:
        messages.error(request, "Cannot link Instagram: User profile missing. Please contact support.")
        return redirect('dashboard')



def privacy_policy_view(request):
    return render(request, 'main_app/privacy_policy.html', {})

def terms_of_service_view(request):
    return render(request, 'main_app/terms_of_service.html', {})


# main_app/views.py (Add this new function)

@login_required
def college_community_chat_view(request):
    """
    Renders the community chat page for the user's college.
    Fetches chat history for the college room.
    """
    user = request.user

    # Check if the user has a profile and a college name
    try:
        user_profile = user.userprofile
        user_college_name = user_profile.college_name

        import re
        if user_college_name:
            room_name_slug = re.sub(r'[^\w\s-]', '', user_college_name).strip().lower().replace(' ', '_')
        else:
            room_name_slug = 'general_community'
            messages.warning(request, "Your college name is not set. You are in a temporary general chat.")

    except UserProfile.DoesNotExist:
        messages.error(request, "Your profile is incomplete. Cannot access community chat.")
        return redirect('dashboard')

    # --- NEW: Fetch Chat History ---
    # Retrieve the last 50 messages for this specific room slug
    chat_history = ChatMessage.objects.filter(
        college_room_slug=room_name_slug
    ).select_related('user').order_by('-timestamp')[:50]

    # Reverse the order so the oldest message is first for display
    chat_history = chat_history[::-1]
    # --- END NEW ---

    context = {
        'college_name': user_college_name,
        'room_name_slug': room_name_slug,  # The sanitized name for Channels routing
        'page_title': f"Chat: {user_college_name}",
        'chat_history': chat_history,  # Pass history to the template
    }

    return render(request, 'main_app/college_community_chat.html', context)


@login_required
@require_POST
def upload_chat_media(request):
    """
    Handles file upload and message saving for the college chat.
    Sends a signal via Channels to notify all connected users.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Not logged in.'}, status=403)

    college_room_slug = request.POST.get('room_name_slug')
    content = request.POST.get('content', '').strip()
    uploaded_file = request.FILES.get('media_file')

    if not college_room_slug:
        return JsonResponse({'status': 'error', 'message': 'Missing room ID.'}, status=400)

    # Security Check: Verify user belongs to this college community
    try:
        user_college_name = request.user.userprofile.college_name
        # Sanitize and compare the user's slug with the provided slug
        user_room_slug = re.sub(r'[^\w\s-]', '', user_college_name).strip().lower().replace(' ', '_')
        if user_room_slug != college_room_slug:
            return JsonResponse({'status': 'error', 'message': 'Unauthorized chat access.'}, status=403)
    except UserProfile.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Profile missing.'}, status=403)


    # --- 1. Save the ChatMessage to the Database ---
    if not content and not uploaded_file:
        return JsonResponse({'status': 'error', 'message': 'Empty message or file.'}, status=400)

    message_type = 'media' if uploaded_file else 'text'

    chat_message = ChatMessage.objects.create(
        college_room_slug=college_room_slug,
        user=request.user,
        content=content if content else None,
        media_file=uploaded_file,
        message_type=message_type
    )

    # --- 2. Send WebSocket Signal ---
    try:
        channel_layer = get_channel_layer()
        room_group_name = 'chat_%s' % college_room_slug

        # Determine media_url safely
        # Note: If uploaded_file is True, chat_message.media_file is NOT None,
        # but the .url access can still fail if storage config is bad. We must assume it's fixed now.
        media_url_safe = chat_message.media_file.url if uploaded_file else ''

        # Determine profile_icon_url safely
        user_profile = request.user.userprofile
        profile_icon_url_safe = user_profile.profile_icon.url if user_profile.profile_icon else ''

        payload = {
            'type': 'chat_message',  # Calls the chat_message method in consumers.py
            'message_id': chat_message.id,
            'sender': request.user.get_full_name() or request.user.username,
            'content': content,
            'message_type': message_type,
            'media_url': media_url_safe,  # Use the safe variable
            'timestamp_str': chat_message.timestamp.strftime('%H:%M'),
            'profile_icon_url': profile_icon_url_safe,  # Use the safe variable
        }

        async_to_sync(channel_layer.group_send)(
            room_group_name,
            payload
        )

    except Exception as e:
        # If Channels signaling fails, log it but let the DB save succeed.
        print(f"CRITICAL CHANNELS ERROR: Failed to send real-time message for ID {chat_message.id}. Error: {e}")
        # Log this error to the server console!
        pass  # Allow the function to continue and return the 'ok' JSON response

        # The function continues here and returns the success response,
        # but now the traceback is logged if the real-time push failed.
    return JsonResponse({'status': 'ok', 'message_id': chat_message.id})


# In main_app/views.py

@login_required
@require_POST
def delete_chat_message(request):
    """
    Allows a user to delete their own chat message, and sends a signal to remove it instantly.
    """
    message_id = request.POST.get('message_id')

    if not message_id:
        return JsonResponse({'status': 'error', 'message': 'Missing message ID.'}, status=400)

    try:
        # 1. Fetch the message, ensuring it belongs to the current user
        message_to_delete = ChatMessage.objects.get(id=message_id, user=request.user)

        # 2. Store the room slug before deletion to send the signal
        room_slug = message_to_delete.college_room_slug

        # 3. Delete the message (deletes media file automatically)
        message_to_delete.delete()

        # 4. Send a WebSocket signal to instantly remove the message for all connected users
        channel_layer = get_channel_layer()
        room_group_name = 'chat_%s' % room_slug

        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                'type': 'chat_delete',  # The new type for the consumer to handle
                'message_id': message_id,
            }
        )

        return JsonResponse({'status': 'ok'})

    except ChatMessage.DoesNotExist:
        # Message not found or the user is trying to delete someone else's message
        return JsonResponse({'status': 'error', 'message': 'Message not found or unauthorized.'}, status=403)
    except Exception as e:
        print(f"ERROR DELETING CHAT MESSAGE: {e}")
        return JsonResponse({'status': 'error', 'message': 'Internal server error during deletion.'}, status=500)


# In main_app/views.py (Replace aptitude_test_setup_view)

@login_required
def screening_setup_view(request, event_link_key, screening_type):
    event = get_object_or_404(Event, event_link_key=event_link_key, organizer=request.user)

    # 1. Handle Setup based on Screening Type
    if screening_type == 'aptitude':
        # --- APTITUDE TEST SETUP LOGIC (REUSED) ---
        try:
            aptitude_test = event.aptitude_test
        except AptitudeTest.DoesNotExist:
            aptitude_test = None

        if request.method == 'POST':
            # Note: We must re-instantiate question_formset on POST for validation
            test_form = AptitudeTestForm(request.POST, instance=aptitude_test)

            if test_form.is_valid():
                aptitude_test_instance = test_form.save(commit=False)
                aptitude_test_instance.event = event
                aptitude_test_instance.save()

                # Get or update the FormSet instance
                question_formset = AptitudeQuestionFormSet(request.POST, instance=aptitude_test_instance)

                if question_formset.is_valid():
                    question_formset.save()
                    messages.success(request, 'Aptitude Test setup complete! Applicants will now be screened.')
                    return redirect('event_log')
                else:
                    messages.error(request, 'There were errors in your questions. Please review them.')
            else:
                messages.error(request, 'Please correct the time and date settings.')
                # Need to re-instantiate question_formset here for failed test_form POST
                question_formset = AptitudeQuestionFormSet(request.POST, instance=aptitude_test)

        else:
            # GET Request
            test_form = AptitudeTestForm(instance=aptitude_test)
            question_formset = AptitudeQuestionFormSet(instance=aptitude_test)

        template_name = 'main_app/aptitude_test_setup.html'
        context_data = {
            'test_form': test_form,
            'question_formset': question_formset,
        }

    elif screening_type == 'video' or screening_type == 'photo':
        # --- VIDEO / PHOTO SCREENING SETUP (SIMPLE REDIRECT) ---
        # Since there are no further settings for video/photo, we just confirm and redirect.
        # If you later need a page to set submission guidelines, you would render a template here.
        if request.method == 'POST':
            # Confirmation logic is simple, assume POST means "I am done with setup"
            messages.success(request,
                             f'{screening_type.title()} Screening selected. Applicants will be prompted to upload their file upon application.')
            return redirect('event_log')
        else:
            # GET request for a simple confirmation page (We don't have this template, so redirect for now)
            # For a real application, you'd render a dedicated 'media_screening_setup.html' here.
            messages.info(request,
                          f'No further setup required for {screening_type.title()} Screening. Redirecting to Event Log.')
            return redirect('event_log')

    else:
        messages.error(request, 'Invalid screening type selected.')
        return redirect('event_log')

    # General context for all paths that render a form (only 'aptitude' path hits this)
    context = {
        'event': event,
        'page_title': f"Setup {screening_type.title()} Screening for {event.event_name}",
        'screening_type': screening_type,
        **context_data
    }

    return render(request, template_name, context)




@login_required
def test_start_page_view(request, event_link_key):
    event = get_object_or_404(Event, event_link_key=event_link_key)

    # Security check: User must have applied AND the test must be set up
    if not EventApplicationDetails.objects.filter(user=request.user, event=event).exists():
        messages.error(request, "You must apply for the event before accessing the test details.")
        return redirect('event_detail', event_link_key=event_link_key)

    try:
        aptitude_test = event.aptitude_test
    except AptitudeTest.DoesNotExist:
        messages.error(request, "Test details are not available for this event.")
        return redirect('dashboard')

    # Check if user has already attempted the test
    attempt = AptitudeTestAttempt.objects.filter(user=request.user, test=aptitude_test).first()
    if attempt:
        messages.warning(request, f"You have already completed this test with a score of {attempt.score} points.")
        return redirect('dashboard')

    now = timezone.now()
    test_start_time = aptitude_test.test_start_date_time

    # ⭐ NEW 10-MINUTE WINDOW END TIME ⭐
    test_access_window_end = test_start_time + timedelta(minutes=10)

    # Determine the test status
    is_test_started = now >= test_start_time
    is_test_window_open = is_test_started and now < test_access_window_end

    # Check if the access window has closed
    if now >= test_access_window_end:
        messages.error(request, "The window to start this aptitude test has closed. Please contact the organizer.")
        return redirect('dashboard')

    # Calculate time remaining for the countdown
    time_difference = None
    time_until_start = None

    if not is_test_started:
        # Before start: Countdown to the official test_start_time
        time_difference = test_start_time - now
        countdown_target_time = test_start_time
        is_grace_period = False
    else:
        # During the 10-minute window: Countdown to the end of the window
        time_difference = test_access_window_end - now
        countdown_target_time = test_access_window_end
        is_grace_period = True

    if time_difference and time_difference.total_seconds() > 0:
        total_seconds = int(time_difference.total_seconds())
        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        time_until_start = {
            'days': days,
            'hours': hours,
            'minutes': minutes,
            'seconds': seconds,
            'is_grace_period': is_grace_period  # Flag for the template
        }

    context = {
        'event': event,
        'aptitude_test': aptitude_test,
        'is_test_available': is_test_window_open,
        'time_until_start': time_until_start,
        'page_title': f"Aptitude Test for {event.event_name}",
        # Pass the countdown target time (either start time or end of window) as a reliably formatted string
        'countdown_target_iso': countdown_target_time.isoformat(),
        'is_grace_period': is_grace_period,
        'local_time_zone': 'Asia/Kolkata'
    }

    return render(request, 'main_app/test_start_page.html', context)

# ... (near the test_start_page_view function) ...

@login_required
def take_aptitude_test_view(request, event_link_key):
    event = get_object_or_404(Event, event_link_key=event_link_key)

    # --- 1. Security and Status Checks ---
    try:
        aptitude_test = event.aptitude_test
    except AptitudeTest.DoesNotExist:
        messages.error(request, "Test is not configured for this event.")
        return redirect('dashboard')

    # Check if the user has applied
    if not EventApplicationDetails.objects.filter(user=request.user, event=event).exists():
        messages.error(request, "You must apply for the event before taking the test.")
        return redirect('event_detail', event_link_key=event_link_key)

    # Check if the test is available (optional: we rely on the start page, but good to check)
    if timezone.now() < aptitude_test.test_start_date_time:
        messages.warning(request, "The test has not started yet.")
        return redirect('test_start_page', event_link_key=event_link_key)

    # Check if user has already attempted the test
    if AptitudeTestAttempt.objects.filter(user=request.user, test=aptitude_test).exists():
        messages.warning(request, "You have already completed this test.")
        return redirect('dashboard')

        # --- 2. Fetch Questions ---
    questions = aptitude_test.questions.all()  # Fetch all related questions

    if not questions.exists():
        messages.error(request, "No questions have been set for this test.")
        return redirect('dashboard')

    if request.method == 'POST':
        # --- 3. POST Handling: Scoring and Saving Attempt ---

        total_score = 0

        # Calculate time taken from a hidden field passed by the form (or session/JS)
        # For simplicity, we assume the form sends 'time_taken_seconds'
        time_taken_seconds = int(request.POST.get('time_taken_seconds', 0))

        # Iterate over submitted answers
        for question in questions:
            # The answer key is formatted as 'q_[question_id]'
            submitted_answer = request.POST.get(f'q_{question.id}')

            # Check if the submitted answer matches the correct answer
            if submitted_answer and submitted_answer.upper() == question.correct_answer.upper():
                total_score += question.points

        # Save the attempt
        AptitudeTestAttempt.objects.create(
            user=request.user,
            test=aptitude_test,
            score=total_score,
            time_taken_seconds=time_taken_seconds
        )

        messages.success(request,
                         f"Test submitted! Your score is {total_score} out of {sum(q.points for q in questions)}.")
        return redirect('dashboard')  # Redirect after successful submission

    # --- 4. GET Handling: Display Test ---
    context = {
        'event': event,
        'aptitude_test': aptitude_test,
        'questions': questions,
        'time_limit_seconds': aptitude_test.time_limit_minutes * 60,  # Total seconds for JS timer
        'page_title': f"Aptitude Test: {event.event_name}",
    }

    return render(request, 'main_app/take_aptitude_test.html', context)



@login_required
@require_POST
def toggle_shortlist_view(request, app_id):
    """
    API endpoint to toggle the 'is_shortlisted' status of a single application.
    The frontend sends the application ID.
    """
    try:
        # 1. Find the application by its ID
        application = EventApplicationDetails.objects.get(pk=app_id)

        # 2. Security Check: Ensure the current user is the organizer of the event
        if application.event.organizer != request.user:
            return JsonResponse({'status': 'error', 'message': 'Unauthorized action.'}, status=403)

        # 3. Toggle the status and save
        application.is_shortlisted = not application.is_shortlisted
        application.save()

        return JsonResponse({
            'status': 'success',
            'is_shortlisted': application.is_shortlisted
        })

    except EventApplicationDetails.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Application not found.'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def shortlisted_applicants_view(request, event_id):
    # 1. Get the event, ensuring the current user is the organizer
    event = get_object_or_404(Event, id=event_id, organizer=request.user)

    # 2. Fetch only the shortlisted applications
    shortlisted_registrations = EventApplicationDetails.objects.filter(
        event=event,
        is_shortlisted=True
    ).order_by('name')

    # ⭐ NEW LOGIC: Use generic submission fetching ⭐
    screening_type = event.screening_type
    applicant_submissions = {}

    if screening_type == 'aptitude':
        if hasattr(event, 'aptitude_test'):
            aptitude_test = event.aptitude_test
            attempts = aptitude_test.attempts.select_related('user')
            for attempt in attempts:
                applicant_submissions[attempt.user.pk] = {
                    'score': attempt.score,
                    'time_taken_seconds': attempt.time_taken_seconds
                }

    elif screening_type == 'video':
        submissions = VideoScreeningSubmission.objects.filter(event=event).select_related('user')
        for sub in submissions:
            applicant_submissions[sub.user.pk] = {'media_url': sub.video_file.url}

    elif screening_type == 'photo':
        submissions = PhotoScreeningSubmission.objects.filter(event=event).select_related('user')
        for sub in submissions:
            applicant_submissions[sub.user.pk] = {'media_url': sub.photo_file.url}

    context = {
        'event': event,
        'registrations': shortlisted_registrations,  # Pass the filtered list
        'screening_type': screening_type,
        'applicant_submissions': applicant_submissions,
        'is_shortlisted_view': True,  # Flag for template title/navigation changes
    }

    # We will reuse the registrations.html template for consistent formatting
    return render(request, 'main_app/registrations.html', context)


# In main_app/views.py (Add the following function)

@login_required
def media_upload_page_view(request, event_link_key, media_type):
    event = get_object_or_404(Event, event_link_key=event_link_key)
    user = request.user

    # 1. Validation: Ensure user has applied and the event requires this type of screening
    if not EventApplicationDetails.objects.filter(user=user, event=event).exists():
        messages.error(request, "You must complete your application before submitting media.")
        return redirect('event_detail', event_link_key=event_link_key)

    if event.screening_type != media_type:
        messages.error(request,
                       f"This event requires {event.screening_type.title()} screening, not {media_type.title()}.")
        return redirect('dashboard')

    # 2. Check for existing submission
    if media_type == 'video':
        SubmissionModel = VideoScreeningSubmission
        UploadForm = VideoSubmissionForm
        file_field = 'video_file'
    else:  # media_type == 'photo'
        SubmissionModel = PhotoScreeningSubmission
        UploadForm = PhotoSubmissionForm
        file_field = 'photo_file'

    if SubmissionModel.objects.filter(user=user, event=event).exists():
        messages.warning(request, f"You have already submitted your {media_type} for this event.")
        return redirect('dashboard')

    # 3. Handle POST Request (Submission)
    if request.method == 'POST':
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.user = user
            submission.event = event
            submission.save()

            messages.success(request, f"Your {media_type} has been successfully submitted!")
            return redirect('dashboard')
        else:
            messages.error(request,
                           f"There was an error with your {media_type} submission. Please check the file type and size.")
    else:
        # 4. Handle GET Request (Display Form)
        form = UploadForm()

    context = {
        'event': event,
        'form': form,
        'media_type': media_type,
        'page_title': f"{media_type.title()} Submission for {event.event_name}",
        'file_field_name': file_field
    }
    return render(request, 'main_app/media_upload_page.html', context)




def state_list_api_view(request):
    """
    Provides a list of canonical state names for an autocomplete field
    from the dedicated State model.
    """
    # 1. Get the query string from the frontend (e.g., 'mah')
    query = request.GET.get('q', '').strip()

    # 2. Filter the clean State model (case-insensitive startswith)
    # We order by name and limit to 10 suggestions for performance.
    states = State.objects.filter(name__istartswith=query).order_by('name')[:10]

    # 3. Format the results as a simple list of strings
    results = [state.name for state in states]

    # 4. Return the list as JSON
    return JsonResponse(results, safe=False)