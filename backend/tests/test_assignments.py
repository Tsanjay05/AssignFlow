import datetime
import pytest

COURSE_ID = "CRS-2026-000001"


@pytest.fixture
def active_course(client):
    """Seed an active course."""
    res = client.post(
        "/api/courses",
        json={
            "id": COURSE_ID,
            "name": "Software Engineering",
            "description": "SE Principles",
            "is_active": True,
        },
    )
    assert res.status_code == 201
    return res.json()


def test_create_assignment_with_rubric(client, active_course):
    """Verify creating an assignment with a nested rubric and criteria."""
    due = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)
    payload = {
        "id": "ASN-2026-000001",
        "course_id": COURSE_ID,
        "title": "Architectural Design Assignment",
        "due_date": due.isoformat(),
        "max_attempts": 2,
        "allow_resubmission": True,
        "rubric": {
            "total_points": 100,
            "criteria": [
                {"name": "Domain Modeling", "max_marks": 50},
                {"name": "Pattern Application", "max_marks": 50},
            ],
        },
    }
    response = client.post("/api/assignments", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "ASN-2026-000001"
    assert data["title"] == "Architectural Design Assignment"
    assert data["is_published"] is False
    assert data["rubric"] is not None
    assert data["rubric"]["total_points"] == 100
    assert len(data["rubric"]["criteria"]) == 2


def test_publish_assignment_success(client, active_course):
    """Verify successfully publishing an assignment that has a due date and rubric."""
    due = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=5)
    payload = {
        "id": "ASN-2026-000002",
        "course_id": COURSE_ID,
        "title": "Publishable Assignment",
        "due_date": due.isoformat(),
        "max_attempts": 1,
        "allow_resubmission": False,
        "rubric": {
            "total_points": 100,
            "criteria": [{"name": "Core Logic", "max_marks": 100}],
        },
    }
    create_res = client.post("/api/assignments", json=payload)
    assert create_res.status_code == 201

    pub_res = client.post("/api/assignments/ASN-2026-000002/publish")
    assert pub_res.status_code == 200
    assert pub_res.json()["is_published"] is True

    # Verify via GET
    get_res = client.get("/api/assignments/ASN-2026-000002")
    assert get_res.status_code == 200
    assert get_res.json()["is_published"] is True


def test_publish_assignment_fails_without_rubric(client, active_course):
    """Verify rejection of publication when assignment has no rubric."""
    due = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=5)
    payload = {
        "id": "ASN-2026-000003",
        "course_id": COURSE_ID,
        "title": "Rubricless Assignment",
        "due_date": due.isoformat(),
        "max_attempts": 1,
        "allow_resubmission": False,
        "rubric": None,
    }
    create_res = client.post("/api/assignments", json=payload)
    assert create_res.status_code == 201

    pub_res = client.post("/api/assignments/ASN-2026-000003/publish")
    assert pub_res.status_code == 400
    assert "rubric" in pub_res.json()["detail"].lower()


def test_list_and_get_assignments(client, active_course):
    """Verify listing assignments with filtering and getting by ID."""
    due = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=3)
    client.post(
        "/api/assignments",
        json={
            "id": "ASN-2026-000004",
            "course_id": COURSE_ID,
            "title": "Assignment 4",
            "due_date": due.isoformat(),
            "max_attempts": 1,
            "allow_resubmission": False,
        },
    )

    list_res = client.get(f"/api/assignments?course_id={COURSE_ID}")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    get_res = client.get("/api/assignments/ASN-2026-000004")
    assert get_res.status_code == 200
    assert get_res.json()["title"] == "Assignment 4"


def test_assignment_not_found(client):
    """Verify 404 for unknown assignment."""
    assert client.get("/api/assignments/ASN-2026-999999").status_code == 404
    assert client.post("/api/assignments/ASN-2026-999999/publish").status_code == 404
