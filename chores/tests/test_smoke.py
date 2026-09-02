"""Smoke tests: the project is wired together and the suite runs green."""

from django.conf import settings


def test_settings_load():
    assert settings.configured


def test_chores_app_installed():
    assert "chores" in settings.INSTALLED_APPS
