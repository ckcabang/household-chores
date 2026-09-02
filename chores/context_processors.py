from .models import Membership


def household(request):
    """Expose the signed-in user's household (if any) to every template.

    Templates use ``current_household`` to decide whether to show the
    "Create a household" nav link.
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    membership = (
        Membership.objects.select_related("household")
        .filter(user=user)
        .first()
    )
    return {
        "current_membership": membership,
        "current_household": membership.household if membership else None,
    }
