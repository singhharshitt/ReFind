"""Context processor that injects navbar badge counts on every page."""

from django.db.models import Q

from .models import Message, Request


def nav_badges(request):
    """Return unread message count and pending request count for the authenticated user."""
    if not request.user.is_authenticated:
        return {'unread_messages': 0, 'pending_received': 0}

    unread = Message.objects.filter(recipient=request.user, is_read=False).count()
    pending = Request.objects.filter(
        listing__owner=request.user,
        status=Request.Status.PENDING,
    ).count()

    return {
        'unread_messages': unread,
        'pending_received': pending,
    }
