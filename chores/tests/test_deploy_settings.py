"""Production settings behaviour.

Settings resolve at import, so these run ``manage.py`` in a subprocess with a
patched environment rather than using the in-process test settings.
"""

import os
import subprocess
import sys

import pytest

BASE = os.getcwd()

PROD_ENV = {
    "DEBUG": "false",
    "SECRET_KEY": "x" * 60,
    "ALLOWED_HOSTS": "chores.example.com",
    "DATABASE_URL": "postgres://u:p@localhost:5432/chores",
    "SECURE_SSL_REDIRECT": "true",
    "SESSION_COOKIE_SECURE": "true",
    "CSRF_COOKIE_SECURE": "true",
    "SECURE_HSTS_SECONDS": "31536000",
}


def run_manage(args, extra_env):
    env = {**os.environ, **extra_env}
    return subprocess.run(
        [sys.executable, "manage.py", *args],
        capture_output=True,
        text=True,
        cwd=BASE,
        env=env,
    )


@pytest.mark.parametrize(
    ("override", "needle"),
    [
        ({"ALLOWED_HOSTS": ""}, "ALLOWED_HOSTS must be set"),
        (
            {"DATABASE_URL": f"sqlite:///{BASE}/db.sqlite3"},
            "Postgres DATABASE_URL is required",
        ),
        ({"DATABASE_URL": ""}, "DATABASE_URL must be set"),
    ],
)
def test_missing_production_config_fails_fast(override, needle):
    result = run_manage(["check"], {**PROD_ENV, **override})
    assert result.returncode != 0
    assert needle in (result.stderr + result.stdout)


def test_check_deploy_reports_no_errors_with_full_config():
    result = run_manage(["check", "--deploy"], PROD_ENV)
    combined = result.stderr + result.stdout
    assert result.returncode == 0, combined
    # Warnings are allowed and triaged in the issue; errors are not.
    assert "ERRORS" not in combined


def test_whitenoise_and_manifest_storage_are_configured():
    code = (
        "from django.conf import settings; "
        "print('whitenoise.middleware.WhiteNoiseMiddleware' in settings.MIDDLEWARE); "
        "print(settings.STORAGES['staticfiles']['BACKEND'])"
    )
    result = run_manage(["shell", "-c", code], PROD_ENV)
    assert "True" in result.stdout
    assert "whitenoise.storage.CompressedManifestStaticFilesStorage" in result.stdout


def test_dev_defaults_still_work_without_any_env():
    # No DEBUG override -> the dev default (True) -> no fail-fast.
    result = run_manage(
        ["check"],
        {
            k: v
            for k, v in os.environ.items()
            if k not in {"DEBUG", "ALLOWED_HOSTS", "DATABASE_URL"}
        },
    )
    assert result.returncode == 0, result.stderr
