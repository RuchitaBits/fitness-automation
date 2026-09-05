from app import calculate_calories


def test_home_and_health(client):
    assert client.get("/").status_code == 200
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json == {"status": "healthy"}


def test_login_success_and_failure(client):
    assert client.post("/login", data={"username": "bad", "password": "bad"}).status_code == 200
    response = client.post("/login", data={"username": "admin", "password": "admin"})
    assert response.status_code == 302
    assert "/dashboard" in response.headers["Location"]


def test_dashboard_requires_login(client):
    assert client.get("/dashboard").status_code == 302


def test_calorie_calculation():
    assert calculate_calories(70, "Fat Loss") == 1540


def test_database_initializes(app):
    with app.app_context():
        from app import query_db
        assert query_db("SELECT username FROM users", one=True)["username"] == "admin"