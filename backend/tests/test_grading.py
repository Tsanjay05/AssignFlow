import datetime
import pytest

COURSE_ID = "CRS-2026-000001"
LEARNER_ID = "LRN-2026-000001"
LEARNER_2_ID = "LRN-2026-000002"
ASSIGNMENT_ID = "ASN-2026-000001"
NO_RESUB_ASSIGNMENT_ID = "ASN-2026-000002"


@pytest.fixture
def grading_setup(client):
    """Seed course, learner, enrollment, assignments (with rubrics), and submissions."""
    # 1. Course
    client.post(
        "/api/courses",
        json={"id": COURSE_ID, "name": "Operating Systems", "is_active": True},
    )

    # 2. Learners
    client.post(
        "/api/learners",
        json={"id": LEARNER_ID, "name": "Meera Sen", "email": "meera@example.com", "is_active": True},
    )
    client.post(
        "/api/learners",
        json={"id": LEARNER_2_ID, "name": "Rohan Gupta", "email": "rohan@example.com", "is_active": True},
    )

    # 3. Enrollments
    client.post(
        "/api/enrollments",
        json={"course_id": COURSE_ID, "learner_id": LEARNER_ID},
    )
    client.post(
        "/api/enrollments",
        json={"course_id": COURSE_ID, "learner_id": LEARNER_2_ID},
    )

    # 4. Standard Assignment with resubmissions allowed
    due_date = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=3)
    client.post(
        "/api/assignments",
        json={
            "id": ASSIGNMENT_ID,
            "course_id": COURSE_ID,
            "title": "Kernel Concurrency",
            "due_date": due_date.isoformat(),
            "max_attempts": 2,
            "allow_resubmission": True,
            "rubric": {
                "total_points": 100,
                "criteria": [
                    {"name": "Synchronization Primitives", "max_marks": 60},
                    {"name": "Deadlock Avoidance", "max_marks": 40},
                ],
            },
        },
    )
    client.post(f"/api/assignments/{ASSIGNMENT_ID}/publish")

    # 5. Assignment with resubmissions disallowed
    client.post(
        "/api/assignments",
        json={
            "id": NO_RESUB_ASSIGNMENT_ID,
            "course_id": COURSE_ID,
            "title": "Strict Final Exam",
            "due_date": due_date.isoformat(),
            "max_attempts": 1,
            "allow_resubmission": False,
            "rubric": {
                "total_points": 100,
                "criteria": [{"name": "All Questions", "max_marks": 100}],
            },
        },
    )
    client.post(f"/api/assignments/{NO_RESUB_ASSIGNMENT_ID}/publish")

    # 6. Create on-time submission (learner 1, attempt 1)
    on_time_res = client.post(
        "/api/submissions",
        json={
            "id": "SUB-2026-000001",
            "assignment_id": ASSIGNMENT_ID,
            "learner_id": LEARNER_ID,
            "submitted_at": (due_date - datetime.timedelta(hours=5)).isoformat(),
        },
    )
    assert on_time_res.status_code == 201

    # 7. Create late submission (learner 2, attempt 1)
    late_res = client.post(
        "/api/submissions",
        json={
            "id": "SUB-2026-000002",
            "assignment_id": ASSIGNMENT_ID,
            "learner_id": LEARNER_2_ID,
            "submitted_at": (due_date + datetime.timedelta(hours=5)).isoformat(),
        },
    )
    assert late_res.status_code == 201


def test_successful_grading_calculates_scores(client, grading_setup):
    """Verify that grading computes raw_score and final_score correctly."""
    # Fetch assignment to get criteria IDs
    asn = client.get(f"/api/assignments/{ASSIGNMENT_ID}").json()
    c1 = asn["rubric"]["criteria"][0]["id"]
    c2 = asn["rubric"]["criteria"][1]["id"]

    payload = {
        "criterion_scores": [
            {"criterion_id": c1, "score": 50.0},
            {"criterion_id": c2, "score": 35.0},
        ],
        "feedback": {
            "comments": "Excellent concurrency control implementation.",
            "strengths": "Clean mutex locking.",
            "improvements": "Consider read-write locks for scalability.",
        },
    }

    res = client.post("/api/submissions/SUB-2026-000001/grade", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["raw_score"] == 85.0
    assert data["late_penalty"] == 0.0
    assert data["final_score"] == 85.0
    assert data["is_passing"] is True
    assert data["feedback"] is not None
    assert data["feedback"]["comments"] == "Excellent concurrency control implementation."

    # Retrieve via GET
    get_res = client.get("/api/submissions/SUB-2026-000001/grade")
    assert get_res.status_code == 200
    assert get_res.json()["final_score"] == 85.0


def test_reject_criterion_score_exceeding_max_marks(client, grading_setup):
    """Verify rejection with 422 if criterion score exceeds rubric max_marks."""
    asn = client.get(f"/api/assignments/{ASSIGNMENT_ID}").json()
    c1 = asn["rubric"]["criteria"][0]["id"]
    c2 = asn["rubric"]["criteria"][1]["id"]

    # Criterion 1 max is 60, passing 65
    payload = {
        "criterion_scores": [
            {"criterion_id": c1, "score": 65.0},
            {"criterion_id": c2, "score": 30.0},
        ]
    }
    res = client.post("/api/submissions/SUB-2026-000001/grade", json=payload)
    assert res.status_code == 422
    assert "exceeds" in res.json()["detail"].lower()


def test_late_penalty_applied_once(client, grading_setup):
    """Verify that late submissions have the late penalty applied exactly once."""
    asn = client.get(f"/api/assignments/{ASSIGNMENT_ID}").json()
    c1 = asn["rubric"]["criteria"][0]["id"]
    c2 = asn["rubric"]["criteria"][1]["id"]

    payload = {
        "criterion_scores": [
            {"criterion_id": c1, "score": 50.0},
            {"criterion_id": c2, "score": 35.0},
        ]
    }

    res = client.post("/api/submissions/SUB-2026-000002/grade", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["raw_score"] == 85.0
    assert data["late_penalty"] == 10.0
    assert data["final_score"] == 75.0

    # Ensure duplicate grading is rejected, preventing duplicate penalty
    res_dup = client.post("/api/submissions/SUB-2026-000002/grade", json=payload)
    assert res_dup.status_code == 400


def test_resubmission_policy_enforcement(client, grading_setup):
    """Verify requesting resubmissions respects assignment policy."""
    # 1. Allowed on ASSIGNMENT_ID
    res1 = client.post(
        "/api/submissions/SUB-2026-000001/resubmit",
        json={"reason": "Fixing edge cases in lock ordering"},
    )
    assert res1.status_code == 201
    assert res1.json()["original_submission_id"] == "SUB-2026-000001"
    assert res1.json()["new_submission_id"] is not None

    # 2. Disallowed on NO_RESUB_ASSIGNMENT_ID
    sub_strict = client.post(
        "/api/submissions",
        json={"assignment_id": NO_RESUB_ASSIGNMENT_ID, "learner_id": LEARNER_ID},
    ).json()

    res2 = client.post(
        f"/api/submissions/{sub_strict['id']}/resubmit",
        json={"reason": "Want another attempt"},
    )
    assert res2.status_code == 400
    assert "not permitted" in res2.json()["detail"].lower()
