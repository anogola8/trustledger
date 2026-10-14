from .models import Notification


def notify(user, message, url=''):
    if user is None:
        return None
    return Notification.objects.create(user=user, message=message[:255], url=url)
