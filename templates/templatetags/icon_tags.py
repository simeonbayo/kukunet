# templatetags/icon_tags.py
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag
def icon(name, **kwargs):
    """Generate an icon HTML tag with classes"""
    classes = ['fas', f'fa-{name}']
    
    if 'class' in kwargs:
        classes.append(kwargs['class'])
        del kwargs['class']
    
    attrs = ' '.join([f'{k}="{v}"' for k, v in kwargs.items()])
    return mark_safe(f'<i class="{" ".join(classes)}" {attrs}></i>')

@register.simple_tag
def role_icon(role):
    """Get icon for user role"""
    icons = {
        'FARMER': 'fas fa-chicken',
        'CUSTOMER': 'fas fa-shopping-cart',
        'SUPPLIER': 'fas fa-box',
        'TRAINER': 'fas fa-chalkboard-user',
        'FIELD_OFFICER': 'fas fa-stethoscope',
        'ORGANIZATION': 'fas fa-building',
        'ADMIN': 'fas fa-user-shield',
        'SUPER_ADMIN': 'fas fa-crown',
    }
    return mark_safe(f'<i class="{icons.get(role, "fas fa-user")}"></i>')

@register.simple_tag
def status_icon(status):
    """Get icon for status"""
    icons = {
        'success': 'fas fa-check-circle text-success',
        'error': 'fas fa-exclamation-circle text-danger',
        'warning': 'fas fa-exclamation-triangle text-warning',
        'info': 'fas fa-info-circle text-info',
        'pending': 'fas fa-clock text-warning',
        'active': 'fas fa-check-circle text-success',
        'inactive': 'fas fa-times-circle text-danger',
    }
    return mark_safe(f'<i class="{icons.get(status, "fas fa-circle")}"></i>')