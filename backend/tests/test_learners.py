import pytest

LEARNER_PAYLOAD = {
    "id": "LRN-2026-000001",
    "name": "Arun Kumar",
    "email": "arun@example.com",
    "is_active": True,
}


def test_create_learner_success(client):
    """1. Create learner successfully."""
    response = client.post("/api/learners", json=LEARNER_PAYLOAD)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == LEARNER_PAYLOAD["id"]
    assert data["name"] == LEARNER_PAYLOAD["name"]
    assert data["email"] == LEARNER_PAYLOAD["email"]
    assert data["is_active"] is True
    assert "created_at" in data


def test_list_learners(client):
    """2. List learners with pagination and filter."""
    client.post("/api/learners", json=LEARNER_PAYLOAD)
    client.post(
        "/api/learners",
        json={
            "id": "LRN-2026-000002",
            "name": "Priya Sharma",
            "email": "priya@example.com",
            "is_active": False,
        },
    )

    res_all = client.get("/api/learners")
    assert res_all.status_code == 200
    assert len(res_all.json()) == 2

    res_active = client.get("/api/learners?is_active=true")
    assert res_active.status_code == 200
    assert len(res_active.json()) == 1
    assert res_active.json()[0]["id"] == "LRN-2026-000001"


def test_get_learner_by_id(client):
    """3. Retrieve learner by ID."""
    client.post("/api/learners", json=LEARNER_PAYLOAD)
    res = client.get(f"/api/learners/{LEARNER_PAYLOAD['id']}")
    assert res.status_code == 200
    assert res.json()["name"] == LEARNER_PAYLOAD["name"]


def test_update_learner(client):
    """4. Update learner partially."""
    client.post("/api/learners", json=LEARNER_PAYLOAD)
    update_res = client.patch(
        f"/api/learners/{LEARNER_PAYLOAD['id']}",
        json={"name": "Arun K.", "email": "arun.new@example.com"},
    )
    assert update_res.status_code == 200
    data = update_res.json()
    assert data["name"] == "Arun K."
    assert data["email"] == "arun.new@example.com"


def test_deactivate_learner(client):
    """5. Deactivate learner softly."""
    client.post("/api/learners", json=LEARNER_PAYLOAD)

    del_res = client.delete(f"/api/learners/{LEARNER_PAYLOAD['id']}")
    assert del_res.status_code == 200
    assert del_res.json()["is_active"] is False

    # Check persistence
    get_res = client.get(f"/api/learners/{LEARNER_PAYLOAD['id']}")
    assert get_res.json()["is_active"] is False

    # Reject duplicate deactivation
    dup_res = client.delete(f"/api/learners/{LEARNER_PAYLOAD['id']}")
    assert dup_res.status_code == 400


def test_reject_duplicate_learner_id(client):
    """6. Reject duplicate learner ID."""
    res1 = client.post("/api/learners", json=LEARNER_PAYLOAD)
    assert res1.status_code == 201

    res2 = client.post(
        "/api/learners",
        json={**LEARNER_PAYLOAD, "email": "different@example.com"},
    )
    assert res2.status_code == 409


def test_reject_duplicate_email(client):
    """7. Reject duplicate email."""
    res1 = client.post("/api/learners", json=LEARNER_PAYLOAD)
    assert res1.status_code == 201

    res2 = client.post(
        "/api/learners",
        json={**LEARNER_PAYLOAD, "id": "LRN-2026-000002"},
    )
    assert res2.status_code == 409


def test_reject_invalid_email(client):
    """8. Reject invalid email formats."""
    invalid_emails = ["not-an-email", "@missing-user.com", "missing-domain@", "user@domain"]
    for bad_email in invalid_emails:
        payload = {**LEARNER_PAYLOAD, "email": bad_email}
        res = client.post("/api/learners", json=payload)
        assert res.status_code == 422, f"Expected 422 for email '{bad_email}'"


def test_return_404_unknown_learner(client):
    """9. Return 404 for unknown learner."""
    unknown_id = "LRN-2026-999999"
    assert client.get(f"/api/learners/{unknown_id}").status_code == 404
    assert client.patch(f"/api/learners/{unknown_id}", json={"name": "Name"}).status_code == 404
    assert client.delete(f"/api/learners/{unknown_id}").status_code == 404
