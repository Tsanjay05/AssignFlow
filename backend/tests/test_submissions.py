import datetime
import pytest

COURSE_ID = "CRS-2026-000001"
LEARNER_ID = "LRN-2026-000001"
UNENROLLED_LEARNER_ID = "LRN-2026-000002"
ASSIGNMENT_ID = "ASN-2026-000001"


@pytest.fixture
def setup_assignment_and_learners(client):
    """Setup Course, Learners, Enrollment, and a Published Assignment."""
    # 1. Create Course
    client.post(
        "/api/courses",
        json={
            "id": COURSE_ID,
            "name": "Distributed Systems",
            "is_active": True,
        },
    )

    # 2. Create Enrolled Learner
    client.post(
        "/api/learners",
        json={
            "id": LEARNER_ID,
            "name": "Kiran Rao",
            "email": "kiran@example.com",
            "is_active": True,
        },
    )

    # 3. Create Unenrolled Learner
    client.post(
        "/api/learners",
        json={
            "id": UNENROLLED_LEARNER_ID,
            "name": "Unenrolled User",
            "email": "unenrolled@example.com",
            "is_active": True,
        },
    )

    # 4. Enroll Learner 1
    client.post(
        "/api/enrollments",
        json={"course_id": COURSE_ID, "learner_id": LEARNER_ID},
    )

    # 5. Create Assignment with Rubric
    due_date = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=2)
    client.post(
        "/api/assignments",
        json={
            "id": ASSIGNMENT_ID,
            "course_id": COURSE_ID,
            "title": "Raft Consensus Algorithm",
            "due_date": due_date.isoformat(),
            "max_attempts": 2,
            "allow_resubmission": True,
            "rubric": {
                "total_points": 100,
                "criteria": [{"name": "Leader Election", "max_marks": 100}],
            },
        },
    )

    # 6. Publish Assignment
    client.post(f"/api/assignments/{ASSIGNMENT_ID}/publish")


def test_successful_valid_submission(client, setup_assignment_and_learners):
    """Verify that an enrolled learner can submit work with artifacts."""
    payload = {
        "id": "SUB-2026-000001",
        "assignment_id": ASSIGNMENT_ID,
        "learner_id": LEARNER_ID,
        "artifacts": [
            {
                "file_name": "raft_impl.py",
                "file_type": "py",
                "file_size_bytes": 4096,
                "storage_path": "/artifacts/SUB-2026-000001/raft_impl.py",
            }
        ],
    }
    response = client.post("/api/submissions", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "SUB-2026-000001"
    assert data["assignment_id"] == ASSIGNMENT_ID
    assert data["learner_id"] == LEARNER_ID
    assert data["attempt_number"] == 1
    assert data["is_late"] is False
    assert len(data["artifacts"]) == 1


def test_reject_submission_unenrolled_learner(client, setup_assignment_and_learners):
    """Verify that an unenrolled learner submission is rejected with 403 Forbidden."""
    payload = {
        "assignment_id": ASSIGNMENT_ID,
        "learner_id": UNENROLLED_LEARNER_ID,
        "artifacts": [],
    }
    response = client.post("/api/submissions", json=payload)
    assert response.status_code == 403
    assert "enrolled" in response.json()["detail"].lower()


def test_enforce_max_attempts(client, setup_assignment_and_learners):
    """Verify that exceeding max_attempts is rejected with 400 Bad Request."""
    # First attempt (allowed)
    res1 = client.post(
        "/api/submissions",
        json={"assignment_id": ASSIGNMENT_ID, "learner_id": LEARNER_ID},
    )
    assert res1.status_code == 201
    assert res1.json()["attempt_number"] == 1

    # Second attempt (allowed, max_attempts = 2)
    res2 = client.post(
        "/api/submissions",
        json={"assignment_id": ASSIGNMENT_ID, "learner_id": LEARNER_ID},
    )
    assert res2.status_code == 201
    assert res2.json()["attempt_number"] == 2

    # Third attempt (rejected)
    res3 = client.post(
        "/api/submissions",
        json={"assignment_id": ASSIGNMENT_ID, "learner_id": LEARNER_ID},
    )
    assert res3.status_code == 400
    assert "maximum" in res3.json()["detail"].lower()


def test_proper_calculation_of_is_late_flag(client, setup_assignment_and_learners):
    """Verify that submissions submitted after due_date are marked is_late=True."""
    # Past submission time (simulating late submission)
    past_due_date = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=10)

    # Submit with simulated late timestamp
    payload = {
        "assignment_id": ASSIGNMENT_ID,
        "learner_id": LEARNER_ID,
        "submitted_at": past_due_date.isoformat(),
    }
    response = client.post("/api/submissions", json=payload)
    assert response.status_code == 201
    assert response.json()["is_late"] is True


def test_reject_submission_to_unpublished_assignment(client, setup_assignment_and_learners):
    """Verify that submissions to unpublished assignments are rejected with 400."""
    due_date = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=2)
    client.post(
        "/api/assignments",
        json={
            "id": "ASN-2026-000099",
            "course_id": COURSE_ID,
            "title": "Unpublished Assignment",
            "due_date": due_date.isoformat(),
            "max_attempts": 1,
            "allow_resubmission": False,
        },
    )

    res = client.post(
        "/api/submissions",
        json={"assignment_id": "ASN-2026-000099", "learner_id": LEARNER_ID},
    )
    assert res.status_code == 400
    assert "unpublished" in res.json()["detail"].lower()


def test_list_and_get_submissions(client, setup_assignment_and_learners):
    """Verify listing and retrieving submissions by ID."""
    sub_res = client.post(
        "/api/submissions",
        json={
            "id": "SUB-2026-000010",
            "assignment_id": ASSIGNMENT_ID,
            "learner_id": LEARNER_ID,
        },
    )
    assert sub_res.status_code == 201

    list_res = client.get(f"/api/submissions?assignment_id={ASSIGNMENT_ID}")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    get_res = client.get("/api/submissions/SUB-2026-000010")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == "SUB-2026-000010"
