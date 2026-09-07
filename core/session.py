from .models import Member


SESSION_MEMBER_ID = "member_id"


def get_active_member(request):
    """Return the active member stored in the request session, if any."""
    if SESSION_MEMBER_ID not in request.session:
        return None

    member_id = request.session[SESSION_MEMBER_ID]
    if not isinstance(member_id, int) or isinstance(member_id, bool):
        request.session.pop(SESSION_MEMBER_ID, None)
        return None

    member = (
        Member.objects.select_related("household")
        .filter(pk=member_id, active=True)
        .first()
    )
    if member is None:
        request.session.pop(SESSION_MEMBER_ID, None)

    return member
