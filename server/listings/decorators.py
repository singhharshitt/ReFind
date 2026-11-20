"""Authorization helpers. Kept for import compatibility; marketplace actions require login only."""

from django.contrib.auth.decorators import login_required


def campus_verified_required(view_func):
    """Require login. Email verification is no longer enforced."""
    return login_required(view_func)
