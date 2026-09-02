"""The base layout renders and the placeholder home page is reachable."""

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_home_page_renders_the_shell(client):
    response = client.get(reverse("chores:home"))
    assert response.status_code == 200
    body = response.content.decode()
    assert "Household Chores" in body
    assert "chores/vendor/htmx-2.0.4.min.js" in body
    assert "chores/vendor/alpinejs-3.14.9.min.js" in body
    assert 'aria-label="Primary"' in body


def test_vendored_assets_are_present(settings):
    vendor = settings.BASE_DIR / "chores" / "static" / "chores" / "vendor"
    assert (vendor / "htmx-2.0.4.min.js").is_file()
    assert (vendor / "alpinejs-3.14.9.min.js").is_file()
