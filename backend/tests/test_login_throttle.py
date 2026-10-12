"""Sign-in throttling keeps a password from being guessed indefinitely."""
import pytest

from conftest import api, routeos_app


PRODUCTION = {"ROUTEOS_DEVELOPMENT_AUTH": "0"}


@pytest.fixture
def secured(monkeypatch, tmp_path):
    monkeypatch.setattr(routeos_app, "DATABASE_PATH", tmp_path / "secure.db")
    monkeypatch.setenv("ROUTEOS_DEVELOPMENT_AUTH", "0")
    # Read at import time, so the constant itself has to be patched.
    monkeypatch.setattr(routeos_app, "LOGIN_MAX_ATTEMPTS", 3)
    with api() as client:
        client.post("/api/v1/users", json={"name": "Batter Driver", "password": "a long unique password"})
        yield client


def attempt(client, password="wrong password", forwarded="10.0.0.5"):
    return client.post("/api/v1/auth/login", headers={"X-Forwarded-For": forwarded},
                       json={"name": "Batter Driver", "password": password})


def test_repeated_wrong_passwords_are_throttled(secured):
    for _ in range(3):
        assert attempt(secured).status_code == 401
    blocked = attempt(secured)
    assert blocked.status_code == 429
    assert "Too many sign-in attempts" in blocked.json()["detail"]


def test_a_correct_password_is_also_refused_while_throttled(secured):
    for _ in range(3):
        attempt(secured)
    assert attempt(secured, password="a long unique password").status_code == 429


def test_successful_sign_in_clears_the_failure_count(secured):
    for _ in range(2):
        assert attempt(secured).status_code == 401
    assert secured.post("/api/v1/auth/login", headers={"X-Forwarded-For": "10.0.0.5"},
                        json={"name": "Batter Driver", "password": "a long unique password"}).status_code == 200
    # The counter restarted, so wrong guesses are accepted for throttling again.
    assert attempt(secured).status_code == 401


def test_throttling_one_account_does_not_lock_another(secured):
    secured.post("/api/v1/users", json={"name": "Second Driver", "password": "another long password"})
    for _ in range(3):
        attempt(secured)
    assert attempt(secured).status_code == 429
    # A different driver on the same network keeps signing in.
    assert secured.post("/api/v1/auth/login", headers={"X-Forwarded-For": "10.0.0.5"},
                        json={"name": "Second Driver", "password": "another long password"}).status_code == 200


def test_one_client_cannot_lock_an_account_for_everyone_else(secured):
    for _ in range(3):
        attempt(secured, forwarded="10.0.0.9")
    assert attempt(secured, forwarded="10.0.0.9").status_code == 429
    # The legitimate driver on another address is unaffected.
    assert attempt(secured, forwarded="10.0.0.5", password="a long unique password").status_code == 200


def test_quick_login_never_counts_as_a_failure(secured, monkeypatch):
    """A passwordless account must not be throttled by ordinary quick sign-in."""
    monkeypatch.setenv("ROUTEOS_DEVELOPMENT_AUTH", "1")
    for _ in range(6):
        assert secured.post("/api/v1/auth/login", headers={"X-Forwarded-For": "10.0.0.5"},
                            json={"name": "Sreekandan Nair"}).status_code == 200


def test_the_window_expires_so_a_locked_driver_recovers(monkeypatch, tmp_path):
    import time as real_time

    monkeypatch.setattr(routeos_app, "DATABASE_PATH", tmp_path / "window.db")
    monkeypatch.setenv("ROUTEOS_DEVELOPMENT_AUTH", "0")
    monkeypatch.setattr(routeos_app, "LOGIN_MAX_ATTEMPTS", 2)
    monkeypatch.setattr(routeos_app, "LOGIN_WINDOW_SECONDS", 60.0)
    # Move the clock past the window rather than sleeping through it.
    start = real_time.monotonic()
    clock = {"now": start}
    monkeypatch.setattr(routeos_app.time, "monotonic", lambda: clock["now"])
    with api() as client:
        client.post("/api/v1/users", json={"name": "Batter Driver", "password": "a long unique password"})
        for _ in range(2):
            client.post("/api/v1/auth/login", headers={"X-Forwarded-For": "10.0.0.5"},
                        json={"name": "Batter Driver", "password": "wrong"})
        assert client.post("/api/v1/auth/login", headers={"X-Forwarded-For": "10.0.0.5"},
                           json={"name": "Batter Driver", "password": "wrong"}).status_code == 429

        # After the window passes the driver signs in normally again.
        clock["now"] = start + 120
        assert client.post("/api/v1/auth/login", headers={"X-Forwarded-For": "10.0.0.5"},
                           json={"name": "Batter Driver",
                                 "password": "a long unique password"}).status_code == 200