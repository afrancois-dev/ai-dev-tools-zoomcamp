from functools import wraps

from django.shortcuts import render

from .session import get_active_member


ACTIVE_MEMBER_ERROR = "You must be an active household member to access this page."
CREATOR_ERROR = "Only the household creator can manage members."


def _authorization_failure(request, message):
    return render(
        request,
        "core/authorization_denied.html",
        {"error": message},
        status=403,
    )


def _authorized_member(request):
    member = get_active_member(request)
    if member is None:
        return None
    return member


def active_member_required(view):
    """Require a valid active session and pass its persisted household to a view."""

    @wraps(view)
    def wrapped(request, *args, **kwargs):
        member = _authorized_member(request)
        if member is None:
            return _authorization_failure(request, ACTIVE_MEMBER_ERROR)

        view_kwargs = dict(kwargs)
        view_kwargs.update(member=member, household=member.household)
        return view(request, *args, **view_kwargs)

    return wrapped


def creator_required(view):
    """Require an active session whose persisted member is the household creator."""

    @wraps(view)
    def wrapped(request, *args, **kwargs):
        member = _authorized_member(request)
        if member is None or member.household.creator_id != member.pk:
            return _authorization_failure(request, CREATOR_ERROR)

        view_kwargs = dict(kwargs)
        view_kwargs.update(member=member, household=member.household)
        return view(request, *args, **view_kwargs)

    return wrapped
