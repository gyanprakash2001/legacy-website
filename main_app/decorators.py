# main_app/decorators.py
from django.shortcuts import redirect
from functools import wraps

def profile_setup_required(view_func):
    """Decorator to enforce mandatory profile fields are set before viewing the dashboard."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            if not request.user.userprofile.setup_complete:
                # Redirects to the dedicated setup page
                return redirect('mandatory_profile_setup')
        return view_func(request, *args, **kwargs)
    return wrapper