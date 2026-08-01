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


# ── admin mode ────────────────────────────────────────────────────────────────
def test_regular_user_is_not_admin(client):
    headers = _auth(client, "regular")
    assert client.get("/api/auth/me", headers=headers).json()["is_admin"] is False


def test_admin_designated_by_env(client, monkeypatch):
    monkeypatch.setenv("COSMIC_ADMIN_USERS", "bosslady, someoneelse")
    headers = _auth(client, "bosslady")
    assert client.get("/api/auth/me", headers=headers).json()["is_admin"] is True


def test_admin_health_requires_admin(client, monkeypatch):
    # Unauthenticated -> 401; authenticated-but-not-admin -> 403.
    assert client.get("/api/admin/health").status_code == 401
    headers = _auth(client, "peon")
    assert client.get("/api/admin/health", headers=headers).status_code == 403


def test_admin_health_returns_metrics_for_admin(client, monkeypatch):
    monkeypatch.setenv("COSMIC_ADMIN_USERS", "chief")
    headers = _auth(client, "chief")
    r = client.get("/api/admin/health", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "uptime_seconds" in data
    assert "total_requests" in data
    assert "status_classes" in data
    assert "recent_errors" in data


def test_admin_health_reports_scene_object_caps(client, monkeypatch):
    """Admins can see how many objects each scene cap kept off the map."""
    from app.metrics import scene_cap_report

    monkeypatch.setenv("COSMIC_ADMIN_USERS", "chief")
    headers = _auth(client, "chief")
    scene_cap_report.record(
        [
            {
                "kind": "satellite",
                "shown": 40,
                "cap": 40,
                "hidden": 11000,
                "hidden_exact": True,
            }
        ]
    )
    try:
        caps = client.get("/api/admin/health", headers=headers).json()["scene_caps"]
    finally:
        scene_cap_report.reset()

    assert caps["total_hidden"] == 11000
    assert caps["kinds"][0]["kind"] == "satellite"


def test_default_admin_bootstrap_login(client):
    from app.api import _ensure_admin_user

    _ensure_admin_user()
    token = client.post(
        "/api/auth/login", json={"username": "admin", "password": "admin"}
    ).json()["token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["is_admin"] is True


# ── user-added scene objects ──────────────────────────────────────────────────
def test_add_list_and_delete_custom_object(client):
    headers = _auth(client, "maker")
    body = {"name": "My Probe", "kind": "satellite", "x_norm": 0.2, "y_norm": -0.1}
    obj = client.post("/api/custom-objects", json=body, headers=headers).json()
    assert obj["source"] == "custom" and obj["name"] == "My Probe"

    listed = client.get("/api/custom-objects", headers=headers).json()["objects"]
    assert len(listed) == 1 and listed[0]["kind"] == "satellite"

    assert (
        client.delete(f"/api/custom-objects/{obj['id']}", headers=headers).status_code
        == 204
    )
    assert client.get("/api/custom-objects", headers=headers).json()["objects"] == []


def test_add_custom_object_requires_auth(client):
    body = {"name": "X", "kind": "satellite", "x_norm": 0.0, "y_norm": 0.0}
    assert client.post("/api/custom-objects", json=body).status_code == 401


def test_add_custom_object_rejects_unknown_kind(client):
    headers = _auth(client, "builder")
    body = {"name": "X", "kind": "dragon", "x_norm": 0.0, "y_norm": 0.0}
    assert (
        client.post("/api/custom-objects", json=body, headers=headers).status_code
        == 422
    )


def test_add_custom_object_rejects_empty_name(client):
    headers = _auth(client, "namer")
    body = {"name": "  ", "kind": "satellite", "x_norm": 0.0, "y_norm": 0.0}
    assert (
        client.post("/api/custom-objects", json=body, headers=headers).status_code
        == 422
    )


def test_custom_objects_are_per_user(client):
    a = _auth(client, "alice_c")
    b = _auth(client, "bob_c")
    client.post(
        "/api/custom-objects",
        json={"name": "A obj", "kind": "comet", "x_norm": 0.1, "y_norm": 0.1},
        headers=a,
    )
    assert client.get("/api/custom-objects", headers=b).json()["objects"] == []


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


def test_admin_health_reports_source_failures(client, monkeypatch):
    """Source outages are hidden from users, so admins must be able to see them."""
    from app.metrics import source_failures

    monkeypatch.setenv("COSMIC_ADMIN_USERS", "chief")
    headers = _auth(client, "chief")
    source_failures.record("simbad", "galaxy", "timeout")
    try:
        data = client.get("/api/admin/health", headers=headers).json()
    finally:
        source_failures.reset()

    assert data["source_failures"]["total"] == 1
    assert data["source_failures"]["sources"][0]["source"] == "simbad"
    assert data["source_failures"]["sources"][0]["kind"] == "galaxy"


def test_per_user_lookups_use_an_index(tmp_path, monkeypatch):
    """Without an index every per-user query full-scans the table."""
    monkeypatch.setenv("COSMIC_DB_PATH", str(tmp_path / "idx.db"))
    from app import db

    db._initialized.clear()
    conn = db.get_conn()
    try:
        for table in ("saved_searches", "saved_uploads", "custom_objects", "sessions"):
            plan = " ".join(
                row["detail"]
                for row in conn.execute(
                    f"EXPLAIN QUERY PLAN SELECT * FROM {table} WHERE user_id = ?", (1,)
                )
            )
            assert "USING INDEX" in plan, f"{table} still scans: {plan}"
    finally:
        conn.close()
        db._initialized.clear()


def test_delete_helpers_refuse_another_users_row(tmp_path, monkeypatch):
    """The shared ownership check is the thing protecting every owned table."""
    monkeypatch.setenv("COSMIC_DB_PATH", str(tmp_path / "own.db"))
    from app import db

    db._initialized.clear()
    owner = db.create_user("owner", None, "h", "s")
    other = db.create_user("other", None, "h", "s")

    search_id = db.add_search(owner, "mine", {"a": 1})
    upload_id = db.add_upload(owner, "f.png", "galaxy", {"class": "g"})
    object_id = db.add_custom_object(owner, "probe", "satellite", 0.1, 0.2)

    assert db.delete_search(other, search_id) is False
    assert db.delete_upload(other, upload_id) is False
    assert db.delete_custom_object(other, object_id) is False

    # ...and the owner can still delete them.
    assert db.delete_search(owner, search_id) is True
    assert db.delete_upload(owner, upload_id) is True
    assert db.delete_custom_object(owner, object_id) is True
    db._initialized.clear()
