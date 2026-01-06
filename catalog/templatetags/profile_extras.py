from django import template
from django.contrib.auth.models import User
from django.conf import settings

register = template.Library()

@register.simple_tag
def student_avatar(student):
    """Return avatar URL for a Student if linked User with profile exists, otherwise default avatar."""
    try:
        user = User.objects.get(username=student.student_id)
        if hasattr(user, 'profile') and user.profile.avatar:
            return user.profile.avatar.url
    except User.DoesNotExist:
        pass
    return settings.MEDIA_URL + 'avatars/red.avif'
