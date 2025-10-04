from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='main_app/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('create-post/', views.create_post, name='create_post'),
    path('events/create/', views.create_event, name='create_event'),
    path('api/events/', views.get_events, name='get_events'),
    path('apply/<uuid:event_link_key>/', views.apply_for_event, name='apply_for_event'),
    path('events/<str:event_title>/', views.event_details, name='event_details'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('', views.index, name='index'),
    path('community/', views.my_community_view, name='my_community'),
    path('event-log/', views.event_log_view, name='event_log'),
    path('event-log/<int:event_id>/registrations/', views.registrations_view, name='registrations'),
    path('college-autocomplete/', views.college_autocomplete, name='college_autocomplete'),
    path('events/filter/', views.filter_events_api, name='filter_events_api'),
    path('calendar-events-api/', views.calendar_events_api, name='calendar_events_api'),
    path('events/day/<str:date_str>/', views.daily_events_view, name='daily_events'),
    path('events/day/<str:date_str>/', views.daily_events_view, name='daily_events'),
    path('community/toggle-follow/', views.toggle_follow_college, name='toggle_follow_college'),
    path('community/<str:college_name>/', views.college_community_view, name='college_community'),
    path('college-autocomplete/', views.college_autocomplete, name='college_autocomplete'),
    path('registrations/<int:event_id>/', views.registrations_view, name='registrations_view'),
    path('my-applications/', views.my_applications_view, name='my_applications'),
    path('api/state-autocomplete/', views.state_autocomplete, name='state_autocomplete'),
    path('profile/', views.profile_view, name='profile'),
    path('cleanup-db/', views.wipe_corrupt_data, name='cleanup_db'),
]


