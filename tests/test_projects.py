import os
from pathlib import Path

from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault(
    "AUTH_USERS_JSON",
    '{"alice":{"password":"alicepass","role":"user"},"bob":{"password":"bobpass","role":"user"},"admin":{"password":"adminpass","role":"admin"}}',
)

from app.main import create_app


def auth_header(client: TestClient, username: str, password: str) -> dict[str, str]:
    response = client.post(
        "/auth/token",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_auth_required(tmp_path: Path) -> None:
    db_path = tmp_path / "auth_required.db"
    app = create_app(f"sqlite:///{db_path}")

    with TestClient(app) as client:
        response = client.get("/projects")
        assert response.status_code == 401


def test_project_crud_flow_user_scoped(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    app = create_app(f"sqlite:///{db_path}")

    with TestClient(app) as client:
        alice_headers = auth_header(client, "alice", "alicepass")
        bob_headers = auth_header(client, "bob", "bobpass")

        create_payload = {
            "name": "Guardians Platform",
            "description": "Registry MVP",
            "owner": "someone-else",
            "expiration_date": "2027-01-01",
        }

        create_response = client.post("/projects", json=create_payload, headers=alice_headers)
        assert create_response.status_code == 201
        created = create_response.json()
        assert created["id"] > 0
        assert created["owner"] == "alice"

        list_response = client.get("/projects", headers=alice_headers)
        assert list_response.status_code == 200
        projects = list_response.json()
        assert len(projects) == 1

        forbidden_list = client.get("/projects", params={"owner": "alice"}, headers=bob_headers)
        assert forbidden_list.status_code == 403

        project_id = created["id"]
        update_response = client.put(
            f"/projects/{project_id}",
            json={"description": "Registry MVP - updated"},
            headers=alice_headers,
        )
        assert update_response.status_code == 200
        assert update_response.json()["description"] == "Registry MVP - updated"

        get_response = client.get(f"/projects/{project_id}", headers=alice_headers)
        assert get_response.status_code == 200
        assert get_response.json()["owner"] == "alice"

        forbidden_get = client.get(f"/projects/{project_id}", headers=bob_headers)
        assert forbidden_get.status_code == 403

        delete_response = client.delete(f"/projects/{project_id}", headers=alice_headers)
        assert delete_response.status_code == 204

        missing_response = client.get(f"/projects/{project_id}", headers=alice_headers)
        assert missing_response.status_code == 404


def test_admin_can_filter_by_owner(tmp_path: Path) -> None:
    db_path = tmp_path / "admin.db"
    app = create_app(f"sqlite:///{db_path}")

    with TestClient(app) as client:
        alice_headers = auth_header(client, "alice", "alicepass")
        bob_headers = auth_header(client, "bob", "bobpass")
        admin_headers = auth_header(client, "admin", "adminpass")

        client.post(
            "/projects",
            json={
                "name": "A",
                "description": "Project A",
                "owner": "alice",
                "expiration_date": "2027-01-01",
            },
            headers=alice_headers,
        )
        client.post(
            "/projects",
            json={
                "name": "B",
                "description": "Project B",
                "owner": "bob",
                "expiration_date": "2027-01-01",
            },
            headers=bob_headers,
        )

        filtered = client.get("/projects", params={"owner": "alice"}, headers=admin_headers)
        assert filtered.status_code == 200
        data = filtered.json()
        assert len(data) == 1
        assert data[0]["owner"] == "alice"
