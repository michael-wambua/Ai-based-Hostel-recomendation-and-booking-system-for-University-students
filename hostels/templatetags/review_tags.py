# Create a file at hostels/templatetags/review_tags.py

from django import template
from django.template.defaultfilters import floatformat

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Gets an item from a dictionary by key"""
    return dictionary.get(int(key), 0)

@register.filter
def percentage(value, total):
    """Calculate percentage with fallback to 0"""
    if total and int(total) > 0:
        return (value / int(total)) * 100
    return 0

@register.filter
def star_range(value):
    """Create a range based on a star rating value"""
    return range(int(floatformat(value, 0)))

@register.filter
def empty_star_range(value):
    """Create a range for empty stars"""
    return range(int(floatformat(value, 0)), 5)