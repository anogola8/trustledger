def unread_count(request):
    user = getattr(request, 'user', None)
    if user is not None and user.is_authenticated:
        return {'unread_notifications': user.notifications.filter(is_read=False).count()}
    return {'unread_notifications': 0}
