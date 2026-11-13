import pytest

COURSE_PAYLOAD = {
    "id": "CRS-2026-000001",
    "name": "Introduction to Computer Science",
    "description": "CS101 Basics",
    "is_active": True,
}


def test_create_course_success(client):
    """1. Create course successfully."""
    response = client.post("/api/courses", json=COURSE_PAYLOAD)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == COURSE_PAYLOAD["id"]
    assert data["name"] == COURSE_PAYLOAD["name"]
    assert data["description"] == COURSE_PAYLOAD["description"]
    assert data["is_active"] is True
    assert "created_at" in data


def test_list_courses(client):
    """2. List courses with pagination and active filtering."""
    client.post("/api/courses", json=COURSE_PAYLOAD)
    client.post(
        "/api/courses",
        json={
            "id": "CRS-2026-000002",
            "name": "Data Structures",
            "description": "CS102 Advanced",
            "is_active": False,
        },
    )

    # List all
    res_all = client.get("/api/courses")
    assert res_all.status_code == 200
    assert len(res_all.json()) == 2

    # Filter active only
    res_active = client.get("/api/courses?is_active=true")
    assert res_active.status_code == 200
    active_items = res_active.json()
    assert len(active_items) == 1
    assert active_items[0]["id"] == "CRS-2026-000001"

    # Pagination: limit
    res_paginated = client.get("/api/courses?limit=1&skip=1")
    assert res_paginated.status_code == 200
    assert len(res_paginated.json()) == 1
    assert res_paginated.json()[0]["id"] == "CRS-2026-000002"


def test_get_course_by_id(client):
    """3. Retrieve course by ID."""
    client.post("/api/courses", json=COURSE_PAYLOAD)
    response = client.get(f"/api/courses/{COURSE_PAYLOAD['id']}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == COURSE_PAYLOAD["id"]
    assert data["name"] == COURSE_PAYLOAD["name"]


def test_update_course(client):
    """4. Update course partially."""
    client.post("/api/courses", json=COURSE_PAYLOAD)

    update_payload = {"name": "Advanced Computer Science", "description": "Updated description"}
    response = client.patch(f"/api/courses/{COURSE_PAYLOAD['id']}", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Advanced Computer Science"
    assert data["description"] == "Updated description"
    assert data["is_active"] is True


def test_deactivate_course(client):
    """5. Deactivate course softly."""
    client.post("/api/courses", json=COURSE_PAYLOAD)

    # Deactivate
    response = client.delete(f"/api/courses/{COURSE_PAYLOAD['id']}")
    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] is False

    # Verify status in database
    get_res = client.get(f"/api/courses/{COURSE_PAYLOAD['id']}")
    assert get_res.json()["is_active"] is False

    # Prevent duplicate deactivation
    dup_res = client.delete(f"/api/courses/{COURSE_PAYLOAD['id']}")
    assert dup_res.status_code == 400


def test_reject_duplicate_course_id(client):
    """6. Reject duplicate course ID."""
    res1 = client.post("/api/courses", json=COURSE_PAYLOAD)
    assert res1.status_code == 201

    res2 = client.post("/api/courses", json=COURSE_PAYLOAD)
    assert res2.status_code == 409


def test_reject_invalid_course_id(client):
    """7. Reject invalid course ID format."""
    invalid_ids = ["INVALID-ID", "CRS-26-000001", "CRS-2026-1", "crs-2026-000001"]
    for bad_id in invalid_ids:
        payload = {**COURSE_PAYLOAD, "id": bad_id}
        res = client.post("/api/courses", json=payload)
        assert res.status_code == 422, f"Expected 422 for ID '{bad_id}'"


def test_reject_empty_course_name(client):
    """8. Reject empty or whitespace-only course name."""
    bad_names = ["", "   ", "\t\n"]
    for bad_name in bad_names:
        payload = {**COURSE_PAYLOAD, "name": bad_name}
        res = client.post("/api/courses", json=payload)
        assert res.status_code == 422, f"Expected 422 for name '{bad_name}'"


def test_return_404_unknown_course(client):
    """9. Return 404 for unknown course."""
    unknown_id = "CRS-2026-999999"
    assert client.get(f"/api/courses/{unknown_id}").status_code == 404
    assert client.patch(f"/api/courses/{unknown_id}", json={"name": "New Name"}).status_code == 404
    assert client.delete(f"/api/courses/{unknown_id}").status_code == 404
