"""Tests for the auth + persistence layer (SQLite-backed)."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # Point the DB at a throwaway file per test.
    monkeypatch.setenv("COSMIC_DB_PATH", str(tmp_path / "cosmic.db"))
    import app.db as db

    db._initialized.clear()
    import app.api as api

    return TestClient(api.app)


def _auth(client, username="stargazer", password="password123"):
    client.post("/api/auth/register", json={"username": username, "password": password})
    token = client.post(
        "/api/auth/login", json={"username": username, "password": password}
    ).json()["token"]
    return {"Authorization": f"Bearer {token}"}


# ── auth ──────────────────────────────────────────────────────────────────────
def test_register_and_login(client):
    r = client.post(
        "/api/auth/register", json={"username": "alice", "password": "password123"}
    )
    assert r.status_code == 200 and r.json()["username"] == "alice"
    r = client.post(
        "/api/auth/login", json={"username": "alice", "password": "password123"}
    )
    assert r.status_code == 200 and "token" in r.json()


def test_register_rejects_duplicate(client):
    client.post(
        "/api/auth/register", json={"username": "bob", "password": "password123"}
    )
    r = client.post(
        "/api/auth/register", json={"username": "bob", "password": "password123"}
    )
    assert r.status_code == 409


def test_register_rejects_short_password(client):
    r = client.post(
        "/api/auth/register", json={"username": "carol", "password": "short"}
    )
    assert r.status_code == 400


def test_login_wrong_password(client):
    client.post(
        "/api/auth/register", json={"username": "dave", "password": "password123"}
    )
    r = client.post(
        "/api/auth/login", json={"username": "dave", "password": "wrongpass1"}
    )
    assert r.status_code == 401


def test_me_requires_and_returns_user(client):
    assert client.get("/api/auth/me").status_code == 401
    headers = _auth(client, "erin")
    r = client.get("/api/auth/me", headers=headers)
    assert r.status_code == 200 and r.json()["username"] == "erin"


def test_me_rejects_bad_token(client):
    r = client.get("/api/auth/me", headers={"Authorization": "Bearer nope"})
    assert r.status_code == 401


def test_logout_invalidates_token(client):
    headers = _auth(client, "frank")
    assert client.get("/api/auth/me", headers=headers).status_code == 200
    client.post("/api/auth/logout", headers=headers)
    assert client.get("/api/auth/me", headers=headers).status_code == 401


# ── theme preference ──────────────────────────────────────────────────────────
def test_theme_defaults_to_none(client):
    headers = _auth(client, "nina")
    assert client.get("/api/auth/me", headers=headers).json()["theme"] is None


def test_save_theme_persists_to_profile(client):
    headers = _auth(client, "opal")
    r = client.put("/api/preferences", json={"theme": "pirate"}, headers=headers)
    assert r.status_code == 200 and r.json()["theme"] == "pirate"
    # The saved theme comes back on the profile.
    assert client.get("/api/auth/me", headers=headers).json()["theme"] == "pirate"


def test_save_theme_requires_auth(client):
    assert client.put("/api/preferences", json={"theme": "pirate"}).status_code == 401


def test_save_theme_rejects_empty(client):
    headers = _auth(client, "pearl")
    r = client.put("/api/preferences", json={"theme": "   "}, headers=headers)
    assert r.status_code == 422


# ── saved searches ────────────────────────────────────────────────────────────
def test_save_list_and_delete_search(client):
    headers = _auth(client, "grace")
    body = {"name": "Orion sweep", "params": {"ra": 83.8, "dec": -5.4}}
    sid = client.post("/api/searches", json=body, headers=headers).json()["id"]

    searches = client.get("/api/searches", headers=headers).json()["searches"]
    assert len(searches) == 1
    assert searches[0]["name"] == "Orion sweep"
    assert searches[0]["params"]["ra"] == 83.8

    assert client.delete(f"/api/searches/{sid}", headers=headers).status_code == 204
    assert client.get("/api/searches", headers=headers).json()["searches"] == []


def test_searches_are_isolated_per_user(client):
    h1 = _auth(client, "heidi")
    h2 = _auth(client, "ivan")
    client.post("/api/searches", json={"name": "mine", "params": {}}, headers=h1)
    assert client.get("/api/searches", headers=h2).json()["searches"] == []


def test_cannot_delete_another_users_search(client):
    h1 = _auth(client, "judy")
    sid = client.post(
        "/api/searches", json={"name": "x", "params": {}}, headers=h1
    ).json()["id"]
    h2 = _auth(client, "mallory")
    assert client.delete(f"/api/searches/{sid}", headers=h2).status_code == 404


def test_searches_require_auth(client):
    assert client.get("/api/searches").status_code == 401


# ── saved uploads ─────────────────────────────────────────────────────────────
def test_save_list_and_delete_upload(client):
    headers = _auth(client, "peggy")
    body = {"filename": "m31.png", "kind": "galaxy", "result": {"conf": 0.9}}
    uid = client.post("/api/uploads", json=body, headers=headers).json()["id"]

    uploads = client.get("/api/uploads", headers=headers).json()["uploads"]
    assert len(uploads) == 1
    assert uploads[0]["filename"] == "m31.png"
    assert uploads[0]["result"]["conf"] == 0.9

    assert client.delete(f"/api/uploads/{uid}", headers=headers).status_code == 204


def test_uploads_are_isolated_per_user(client):
    h1 = _auth(client, "trent")
    h2 = _auth(client, "walter")
    client.post("/api/uploads", json={"filename": "a.png", "result": {}}, headers=h1)
    assert client.get("/api/uploads", headers=h2).json()["uploads"] == []


def test_cannot_delete_another_users_upload(client):
    h1 = _auth(client, "sybil")
    uid = client.post(
        "/api/uploads", json={"filename": "a.png", "result": {}}, headers=h1
    ).json()["id"]
    h2 = _auth(client, "victor")
    assert client.delete(f"/api/uploads/{uid}", headers=h2).status_code == 404


def test_delete_missing_upload_returns_404(client):
    headers = _auth(client, "oscar")
    assert client.delete("/api/uploads/99999", headers=headers).status_code == 404


def test_uploads_require_auth(client):
    assert client.get("/api/uploads").status_code == 401
    assert (
        client.post("/api/uploads", json={"filename": "x", "result": {}}).status_code
        == 401
    )


# ── unit: hashing ─────────────────────────────────────────────────────────────
def test_password_hash_roundtrip():
    from app import auth

    digest, salt = auth.hash_password("hunter2secret")
    assert auth.verify_password("hunter2secret", salt, digest)
    assert not auth.verify_password("wrongpassword", salt, digest)
    # A fresh call uses a new random salt.
    digest2, salt2 = auth.hash_password("hunter2secret")
    assert salt2 != salt
