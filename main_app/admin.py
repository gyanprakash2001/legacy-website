from django.contrib import admin
from .models import UserProfile, Event, Post
from .models import EventCategory, EventType, College, State
from .models import EventApplicationDetails

admin.site.register(UserProfile)
admin.site.register(Event)
admin.site.register(Post)
admin.site.register(EventCategory)
admin.site.register(EventType)
admin.site.register(College)
admin.site.register(EventApplicationDetails)
admin.site.register(State)