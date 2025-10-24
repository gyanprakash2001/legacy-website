# main_app/templatetags/custom_filters.py

from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Allows dictionary key lookups by variable key in Django templates."""
    return dictionary.get(key)