"""Settings are environment-driven with a zero-config local default."""

import environ


def test_local_default_database_is_sqlite(settings):
    assert settings.DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3"


def test_database_url_is_parsed_for_postgres():
    config = environ.Env().db_url_config("postgres://user:pw@dbhost:5432/chores")
    assert config["ENGINE"] == "django.db.backends.postgresql"
    assert config["NAME"] == "chores"
    assert config["HOST"] == "dbhost"


def test_debug_and_secret_key_come_from_settings(settings):
    assert isinstance(settings.DEBUG, bool)
    assert settings.SECRET_KEY
