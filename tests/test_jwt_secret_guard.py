"""
Audit fix regression (Critical, dimension 1): app/auth/jwt_utils.py must
refuse to start on the public, well-known dev secret outside dev/test.
SECRET_KEY is computed once at import time, so this has to run in a fresh
subprocess per case rather than monkeypatching os.environ in-process.
"""
import subprocess
import sys


def _run(env_overrides: dict) -> subprocess.CompletedProcess:
    code = "import app.auth.jwt_utils"
    return subprocess.run(
        [sys.executable, "-c", code],
        env=env_overrides,
        capture_output=True,
        text=True,
    )


def test_refuses_to_start_on_dev_default_in_production(tmp_path):
    result = _run({"PATH": "/usr/bin:/bin", "APP_ENV": "production"})
    assert result.returncode != 0
    assert "AUTH_SECRET_KEY" in result.stderr


def test_allows_the_dev_default_when_app_env_is_dev(tmp_path):
    result = _run({"PATH": "/usr/bin:/bin", "APP_ENV": "dev"})
    assert result.returncode == 0


def test_allows_the_dev_default_when_app_env_is_unset(tmp_path):
    result = _run({"PATH": "/usr/bin:/bin"})
    assert result.returncode == 0


def test_allows_production_when_a_real_secret_is_set(tmp_path):
    result = _run({"PATH": "/usr/bin:/bin", "APP_ENV": "production", "AUTH_SECRET_KEY": "a-real-secret"})
    assert result.returncode == 0
