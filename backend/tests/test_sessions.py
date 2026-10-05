from conftest import api
from conftest import routeos_app
from contextlib import closing


def test_production_password_session_and_revocation(monkeypatch):
    monkeypatch.setenv("ROUTEOS_DEVELOPMENT_AUTH", "0")
    with api() as client:
        assert client.post("/api/v1/auth/login", json={"name": "D.B Cooper"}).status_code == 401
        assert client.post("/api/v1/users", json={"name": "No password"}).status_code == 422
        account = {"name": "Password Driver", "password": "a long unique test password"}
        assert client.post("/api/v1/users", json=account).status_code == 201
        assert client.post("/api/v1/auth/login", json={**account, "password": "wrong"}).status_code == 401
        session = client.post("/api/v1/auth/login", json=account).json()
        headers = {"Authorization": "Bearer " + session["auth_token"]}
        assert client.get("/api/v1/routes", headers=headers).status_code == 200
        assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200
        assert client.get("/api/v1/routes", headers=headers).status_code == 401


def test_expired_bearer_session_is_rejected(monkeypatch):
    monkeypatch.setenv("ROUTEOS_DEVELOPMENT_AUTH", "0")
    with api() as client:
        account = {"name": "Expired Driver", "password": "another unique test password"}
        client.post("/api/v1/users", json=account)
        session = client.post("/api/v1/auth/login", json=account).json()
        with closing(routeos_app.connection()) as db, db:
            db.execute("UPDATE sessions SET expires_at='2000-01-01T00:00:00+00:00' WHERE user_id=?", (session['id'],))
        assert client.get("/api/v1/routes", headers={"Authorization": "Bearer " + session['auth_token']}).status_code == 401


def test_secure_password_provisioning_for_an_existing_account(monkeypatch):
    import provision_password
    with api() as client:
        client.post("/api/v1/users", json={"name": "Provision Driver"})
        monkeypatch.setattr("sys.argv", ["provision_password.py", "Provision Driver"])
        monkeypatch.setattr(provision_password.getpass, "getpass", lambda prompt: "provisioned unique password")
        provision_password.main()
        monkeypatch.setenv("ROUTEOS_DEVELOPMENT_AUTH", "0")
        assert client.post("/api/v1/auth/login", json={"name": "Provision Driver", "password": "provisioned unique password"}).status_code == 200


def test_render_demo_password_provisions_seeded_accounts_on_startup(monkeypatch):
    monkeypatch.setenv("ROUTEOS_DEVELOPMENT_AUTH", "0")
    monkeypatch.setenv("ROUTEOS_DEMO_PASSWORD", "Demo123Route")
    with api() as client:
        response = client.post(
            "/api/v1/auth/login",
            json={"name": "Sreekandan Nair", "password": "Demo123Route"},
        )
        assert response.status_code == 200
