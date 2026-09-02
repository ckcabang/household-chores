from django.contrib.auth.forms import UserCreationForm


class SignupForm(UserCreationForm):
    """Account signup form.

    A thin subclass of Django's :class:`UserCreationForm` so the fields
    (username, password, password confirmation) and all validation -
    duplicate usernames, password mismatch, and ``AUTH_PASSWORD_VALIDATORS`` -
    come straight from ``django.contrib.auth``.
    """

    class Meta(UserCreationForm.Meta):
        pass
