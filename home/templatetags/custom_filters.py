from django import template
from datetime import datetime

register = template.Library()

@register.filter
def timestamp_to_date(value):
    try:
        timestamp = int(value)
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
    except ValueError:
        return value

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)