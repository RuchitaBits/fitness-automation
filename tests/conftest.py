import secrets

import pytest

from app import create_app


@pytest.fixture()
def app(tmp_path):
    test_secret_key = secrets.token_urlsafe(32)
    test_password = secrets.token_urlsafe(24)
    return create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "test.db"),
            "SECRET_KEY": test_secret_key,
            "DEMO_USERNAME": "test-coach",
            "DEMO_PASSWORD": test_password,
            "APP_VERSION": "test-version",
        }
    )


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def logged_in(client):
    client.post(
        "/login",
        data={
            "username": client.application.config["DEMO_USERNAME"],
            "password": client.application.config["DEMO_PASSWORD"],
        },
    )
    return client