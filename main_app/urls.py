from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # ------------------ New Public Index Page (Root) -------------------
    # 1. Root Path: Points to the static index page (the public splash page).
    path('', views.index, name='index'),

    # 2. Registration Choice Page: Moved to /signup/
    path('signup/', views.register_choice_view, name='register_choice'),

    # ------------------ Core Flow Entry Points -------------------
    # 3. Email Registration Form
    path('register/', views.register_view, name='register'),

    # 4. Social Login Flow Start and Success Handler
    path('social/start/', views.social_login_start_view, name='social_login_start'),
    path('social-login-success/', views.social_login_view, name='social_login_success'),

    # 5. Mandatory Profile Setup (The Form Processor)
    path('setup/mandatory/', views.mandatory_profile_setup_view, name='mandatory_profile_setup'),

    # ------------------ Authentication -------------------
    path('login/', auth_views.LoginView.as_view(template_name='main_app/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # ------------------ Dashboard & Content Views (Keep these intact) -------------------
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('community/', views.my_community_view, name='my_community'),
    path('college-community/<str:college_name>/', views.college_community_view, name='college_community'),

    # ... (rest of the event, post, and API paths remain below) ...
    path('create-post/', views.create_post, name='create_post'),
    path('events/create/', views.create_event, name='create_event'),
    path('apply/<uuid:event_link_key>/', views.apply_for_event, name='apply_for_event'),
    path('events/<str:event_title>/', views.event_details, name='event_details'),
    path('event-log/', views.event_log_view, name='event_log'),
    path('registrations/<int:event_id>/', views.registrations_view, name='registrations_view'),
    path('my-applications/', views.my_applications_view, name='my_applications'),
    path('api/events/', views.get_events, name='get_events'),
    path('events/filter/', views.filter_events_api, name='filter_events_api'),
    path('calendar-events-api/', views.calendar_events_api, name='calendar_events_api'),
    path('events/day/<str:date_str>/', views.daily_events_view, name='daily_events'),
    path('college-autocomplete/', views.college_autocomplete, name='college_autocomplete'),
    path('api/state-autocomplete/', views.state_autocomplete, name='state_autocomplete'),
    path('api/state-list-new/', views.state_list_api_view, name='state_list_api'),
    path('community/toggle-follow/', views.toggle_follow_college, name='toggle_follow_college'),
    path('event/<uuid:event_link_key>/', views.event_detail_view, name='event_detail'),
    path('community/chat/', views.college_community_chat_view, name='college_community_chat'),
    path('community/chat/upload/', views.upload_chat_media, name='upload_chat_media'),
    path('community/chat/delete/', views.delete_chat_message, name='delete_chat_message'),
    path('apply/<uuid:event_link_key>/test/start/', views.test_start_page_view, name='test_start_page'),
    path('apply/<uuid:event_link_key>/test/take/', views.take_aptitude_test_view, name='take_aptitude_test'),
    path('events/setup-screening/<uuid:event_link_key>/<str:screening_type>/', views.screening_setup_view, name='screening_setup'),
    path('events/<uuid:event_link_key>/<str:media_type>/upload/', views.media_upload_page_view, name='media_upload_page'),
    path('registrations/toggle-shortlist/<int:app_id>/', views.toggle_shortlist_view, name='toggle_shortlist'),
    path('registrations/<int:event_id>/shortlisted/', views.shortlisted_applicants_view, name='shortlisted_applicants'),
]