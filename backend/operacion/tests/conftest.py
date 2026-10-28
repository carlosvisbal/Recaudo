import pytest


@pytest.fixture(autouse=True)
def _media_root(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    settings.EMAIL_HOST = ""
    settings.EMAIL_HOST_USER = ""
