from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout
from django.utils import timezone
from django.contrib import messages
from django.http import Http404
from django.db import IntegrityError
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from django.db.models import Q, F  # Ensure F is imported at the top of your views.py
from .models import Event, Post, UserProfile, MediaFile, EventApplicationDetails, Follow, College, EventCategory, \
    EventType
from .forms import UserRegistrationForm, PostForm, EventCreationForm, EventApplicationForm, UserUpdateForm, UserProfileUpdateForm
from datetime import datetime
from django.views.decorators.http import require_POST





def index(request):
    return render(request, 'main_app/index.html')


def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()

            college_name_obj = form.cleaned_data.get('college_name')
            profile_icon = request.FILES.get('profile_icon')

            UserProfile.objects.create(
                user=user,
                college_name=college_name_obj.name,
                profile_icon=profile_icon
            )

            try:
                Follow.objects.create(follower=user, college_name=college_name_obj.name)
            except IntegrityError:
                pass

            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('dashboard')
    else:
        form = UserRegistrationForm()

    colleges = College.objects.all().order_by('name')
    return render(request, 'main_app/register.html', {'form': form, 'colleges': colleges})


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
    logout(request)
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
def dashboard(request):
    user = request.user

    # 1. Get the list of college names the user is following via the Follow model
    followed_college_names = list(Follow.objects.filter(follower=user).values_list('college_name', flat=True))

    # 2. Get the user's own college name (This ensures posts from their college are always seen)
    user_college_name = user.userprofile.college_name if hasattr(user, 'userprofile') else None

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

    # --- MISSING LOGIC ADDED HERE ---
    # Fetch the suggested colleges needed for the right sidebar
    # We must handle the case where the UserProfile might not exist
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
    # --- END MISSING LOGIC ---

    # Ensure posts_list is passed in the context
    context = {
        'posts_list': posts_list,
        'upcoming_events': upcoming_events,
        'suggested_colleges': suggested_colleges,
        'categories_with_types': categories_with_types,
    }

    return render(request, 'main_app/dashboard.html', context)

@login_required
def create_event(request):
    event_link = None
    initial_data = {}

    # --- 1. DEFINE CATEGORIES EARLY (Fixes NameError) ---
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
    user_college_state = None
    try:
        user_profile = request.user.userprofile
        user_college_name_str = user_profile.college_name

        # Extract State using the robust rsplit method (as discussed)
        separator = ' - '
        if separator in user_college_name_str:
            state_parts = user_college_name_str.rsplit(separator, 1)
            user_college_state = state_parts[-1].strip()

    except UserProfile.DoesNotExist:
        pass
    except Exception:
        pass

    if user_college_state:
        initial_data['state'] = user_college_state

    # --- 3. HANDLE REQUEST METHOD ---
    if request.method == 'POST':
        form = EventCreationForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.save()
            messages.success(request, 'Event created successfully!')
            return redirect('dashboard')
    else:
        # GET Request: Initialize form with autofilled data
        form = EventCreationForm(initial=initial_data)

    # The final return now correctly uses the form and categories_with_types (defined at the start).
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
            return redirect('dashboard')
    else:
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




@login_required
def registrations_view(request, event_id):
    # Get the specific event or return a 404 error
    event = get_object_or_404(Event, id=event_id, organizer=request.user)

    # Get all applications for this specific event
    registrations = EventApplicationDetails.objects.filter(event=event).order_by('name')

    context = {
        'event': event,
        'registrations': registrations
    }
    return render(request, 'main_app/registrations.html', context)


def college_autocomplete(request):
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


from django.shortcuts import redirect
from django.contrib.auth.decorators import user_passes_test
from django.db import connection


@user_passes_test(lambda u: u.is_superuser)
def wipe_corrupt_data(request):
    """Uses TRUNCATE to quickly clear corrupted Post and Event data."""
    if request.user.is_superuser:
        with connection.cursor() as cursor:
            # CRITICAL: TRUNCATE bypasses ORM safety checks and is aggressive.
            # This is necessary because the ORM delete() is failing.
            cursor.execute("TRUNCATE TABLE main_app_post RESTART IDENTITY CASCADE;")
            cursor.execute("TRUNCATE TABLE main_app_event RESTART IDENTITY CASCADE;")

    # Redirect to the Dashboard for confirmation
    return redirect('dashboard')