import importlib
import sqlite3

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app_client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("SECRET_KEY", "test-secret")

    import app

    app = importlib.reload(app)
    with TestClient(app.app) as client:
        yield client, app


def login(client, username):
    return client.post(
        "/login",
        data={"username": username, "password": "campus123"},
        follow_redirects=False,
    )


def test_health_check(app_client):
    client, _ = app_client
    assert client.get("/health").json() == {"ok": True}


def test_download_requires_sign_in(app_client):
    client, _ = app_client
    response = client.get("/download/1", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_starter_traversal_url_no_longer_works(app_client):
    client, _ = app_client
    response = client.get("/download?name=../private/grader.txt")
    assert response.status_code == 404
    assert b"DROP-5521" not in response.content


def test_user_can_download_own_file_but_not_another_users(app_client):
    client, app = app_client

    assert login(client, "maya").status_code == 303
    own_file = client.get("/download/1")
    assert own_file.status_code == 200
    assert b"Lab 1" in own_file.content

    with sqlite3.connect(app.DB_PATH) as conn:
        devon_id = conn.execute(
            "SELECT id FROM users WHERE username = 'devon'"
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO files (user_id, stored_name, original_name) VALUES (?, ?, ?)",
            (devon_id, "../private/grader.txt", "grader.txt"),
        )
        devon_file_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    forbidden = client.get(f"/download/{devon_file_id}")
    assert forbidden.status_code == 404
    assert b"DROP-5521" not in forbidden.content


def test_upload_keeps_original_name_and_stays_inside_uploads(app_client):
    client, app = app_client
    login(client, "devon")

    response = client.post(
        "/upload",
        files={"file": ("lab2.txt", b"Devon's lab", "text/plain")},
        follow_redirects=False,
    )
    assert response.status_code == 303

    with sqlite3.connect(app.DB_PATH) as conn:
        row = conn.execute(
            "SELECT id, stored_name, original_name FROM files ORDER BY id DESC LIMIT 1"
        ).fetchone()

    assert row[2] == "lab2.txt"
    stored_path = app.upload_path(row[1])
    assert stored_path is not None
    assert stored_path.read_bytes() == b"Devon's lab"

    downloaded = client.get(f"/download/{row[0]}")
    assert downloaded.status_code == 200
    assert downloaded.content == b"Devon's lab"
    assert 'filename="lab2.txt"' in downloaded.headers["content-disposition"]


def test_upload_rejects_directory_traversal_filename(app_client):
    client, app = app_client
    login(client, "devon")

    response = client.post(
        "/upload",
        files={"file": ("../private/changed.txt", b"bad", "text/plain")},
    )

    assert response.status_code == 400
    assert not (app.PRIVATE / "changed.txt").exists()

    windows_style = client.post(
        "/upload",
        files={"file": (r"..\private\changed.txt", b"bad", "text/plain")},
    )
    assert windows_style.status_code == 400
