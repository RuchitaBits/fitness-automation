import secrets

from app import calculate_calories, create_app


def test_home_and_health(client):
    assert client.get("/").status_code == 200
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json == {"status": "healthy"}
    assert response.headers["X-Application-Version"] == "test-version"


def test_login_success_and_failure(client):
    assert client.post("/login", data={"username": "bad", "password": "bad"}).status_code == 200
    response = client.post(
        "/login",
        data={
            "username": client.application.config["DEMO_USERNAME"],
            "password": client.application.config["DEMO_PASSWORD"],
        },
    )
    assert response.status_code == 302
    assert "/dashboard" in response.headers["Location"]


def test_dashboard_requires_login(client):
    assert client.get("/dashboard").status_code == 302


def test_calorie_calculation():
    assert calculate_calories(70, "Fat Loss") == 1540


def test_database_initializes(app):
    with app.app_context():
        from app import query_db
        assert query_db("SELECT username FROM users", one=True)["username"] == "test-coach"


def test_login_fails_closed_without_authentication_configuration(tmp_path, monkeypatch):
    for key in (
        "SECRET_KEY",
        "FLASK_SECRET_KEY",
        "DEMO_USERNAME",
        "ADMIN_USERNAME",
        "DEMO_PASSWORD",
        "ADMIN_PASSWORD",
    ):
        monkeypatch.delenv(key, raising=False)

    app = create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "unconfigured.db"),
            "SECRET_KEY": None,
            "DEMO_USERNAME": None,
            "DEMO_PASSWORD": None,
        }
    )

    response = app.test_client().post("/login", data={})

    assert response.status_code == 503


def test_devops_environment_names_configure_the_existing_application(tmp_path, monkeypatch):
    database_path = tmp_path / "devops.db"
    admin_password = secrets.token_urlsafe(24)
    secret_key = secrets.token_urlsafe(32)
    monkeypatch.setenv("ADMIN_USERNAME", "env-coach")
    monkeypatch.setenv("ADMIN_PASSWORD", admin_password)
    monkeypatch.setenv("FLASK_SECRET_KEY", secret_key)
    monkeypatch.setenv("ACEEST_DB_PATH", str(database_path))
    monkeypatch.setenv("APP_VERSION", "3.2.4")

    app = create_app({"TESTING": True})

    assert app.config["DEMO_USERNAME"] == "env-coach"
    assert app.config["DEMO_PASSWORD"] == admin_password
    assert app.config["SECRET_KEY"] == secret_key
    assert app.config["DATABASE"] == str(database_path)
    assert app.test_client().get("/health").headers["X-Application-Version"] == "3.2.4"


def test_shadow_mode_does_not_persist_state_changing_requests(logged_in, tmp_path):
    primary_app = logged_in.application
    shadow_app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": primary_app.config["SECRET_KEY"],
            "DEMO_USERNAME": primary_app.config["DEMO_USERNAME"],
            "DEMO_PASSWORD": primary_app.config["DEMO_PASSWORD"],
            "DATABASE": str(tmp_path / "shadow.db"),
            "SHADOW_MODE": True,
        }
    )
    shadow_client = shadow_app.test_client()
    session_cookie = logged_in.get_cookie("session")
    shadow_client.set_cookie("session", session_cookie.value)

    response = shadow_client.post(
        "/clients/add",
        data={
            "name": "Shadow Client",
            "age": 30,
            "height": 170,
            "weight": 70,
            "target_weight": 65,
            "program": "Fat Loss",
        },
    )

    assert response.status_code == 202
    with shadow_app.app_context():
        from app import query_db

        assert query_db("SELECT COUNT(*) AS count FROM clients", one=True)["count"] == 0