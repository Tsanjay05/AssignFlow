import datetime
import pytest

COURSE_ID = "CRS-2026-000001"
LEARNER_ID = "LRN-2026-000001"
ASSIGNMENT_ID = "ASN-2026-000001"


@pytest.fixture
def appeal_setup(client):
    """Seed graded submission ready for an appeal."""
    # 1. Course
    client.post(
        "/api/courses",
        json={"id": COURSE_ID, "name": "Computer Networks", "is_active": True},
    )

    # 2. Learner
    client.post(
        "/api/learners",
        json={"id": LEARNER_ID, "name": "Aditi Sharma", "email": "aditi@example.com", "is_active": True},
    )

    # 3. Enrollment
    client.post(
        "/api/enrollments",
        json={"course_id": COURSE_ID, "learner_id": LEARNER_ID},
    )

    # 4. Assignment
    due_date = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=3)
    client.post(
        "/api/assignments",
        json={
            "id": ASSIGNMENT_ID,
            "course_id": COURSE_ID,
            "title": "TCP Congestion Control Simulation",
            "due_date": due_date.isoformat(),
            "max_attempts": 2,
            "allow_resubmission": True,
            "rubric": {
                "total_points": 100,
                "criteria": [{"name": "Simulation Accuracy", "max_marks": 100}],
            },
        },
    )
    client.post(f"/api/assignments/{ASSIGNMENT_ID}/publish")

    # 5. Submission
    client.post(
        "/api/submissions",
        json={
            "id": "SUB-2026-000001",
            "assignment_id": ASSIGNMENT_ID,
            "learner_id": LEARNER_ID,
        },
    )

    # 6. Grade
    asn = client.get(f"/api/assignments/{ASSIGNMENT_ID}").json()
    crit_id = asn["rubric"]["criteria"][0]["id"]
    grade_res = client.post(
        "/api/submissions/SUB-2026-000001/grade",
        json={"criterion_scores": [{"criterion_id": crit_id, "score": 75.0}]},
    )
    assert grade_res.status_code == 201
    return grade_res.json()


def test_file_appeal_and_approve_generates_audit(client, appeal_setup):
    """Verify filing an appeal, approving it, and confirming automatic GradeAudit creation."""
    grade_id = appeal_setup["id"]
    original_score = appeal_setup["final_score"]
    assert original_score == 75.0

    # 1. File appeal
    appeal_res = client.post(
        f"/api/grades/{grade_id}/appeal",
        json={"reason": "Incorrect deduction on slow-start threshold graph."},
    )
    assert appeal_res.status_code == 201
    appeal = appeal_res.json()
    appeal_id = appeal["id"]
    assert appeal["status"] == "pending"
    assert appeal["original_score"] == 75.0

    # 2. Approve appeal with revised score 88.0
    patch_res = client.patch(
        f"/api/appeals/{appeal_id}",
        json={
            "status": "approved",
            "updated_score": 88.0,
            "reason": "Re-evaluated graph submission; approved 13-point increase.",
        },
    )
    assert patch_res.status_code == 200
    updated_appeal = patch_res.json()
    assert updated_appeal["status"] == "approved"
    assert updated_appeal["updated_score"] == 88.0

    # 3. Verify grade was updated
    grade_check = client.get("/api/submissions/SUB-2026-000001/grade").json()
    assert grade_check["final_score"] == 88.0

    # 4. CRITICAL: Verify GradeAudit was created automatically
    audit_res = client.get(f"/api/grades/{grade_id}/audit")
    assert audit_res.status_code == 200
    audits = audit_res.json()
    assert len(audits) == 1
    assert audits[0]["grade_id"] == grade_id
    assert audits[0]["previous_score"] == 75.0
    assert audits[0]["new_score"] == 88.0
    assert "approved" in audits[0]["change_reason"].lower()


def test_appeal_rejection_leaves_score_intact(client, appeal_setup):
    """Verify rejecting an appeal leaves final_score intact and does not add a score-change audit."""
    grade_id = appeal_setup["id"]

    appeal_res = client.post(
        f"/api/grades/{grade_id}/appeal",
        json={"reason": "Requesting extra marks."},
    )
    appeal_id = appeal_res.json()["id"]

    reject_res = client.patch(
        f"/api/appeals/{appeal_id}",
        json={"status": "rejected"},
    )
    assert reject_res.status_code == 200
    assert reject_res.json()["status"] == "rejected"

    # Score remains 75.0
    grade_check = client.get("/api/submissions/SUB-2026-000001/grade").json()
    assert grade_check["final_score"] == 75.0

    # No score revision audit recorded
    audit_res = client.get(f"/api/grades/{grade_id}/audit")
    assert len(audit_res.json()) == 0


def test_reject_modifying_already_decided_appeal(client, appeal_setup):
    """Verify that an appeal cannot be decided twice."""
    grade_id = appeal_setup["id"]
    appeal_id = client.post(
        f"/api/grades/{grade_id}/appeal",
        json={"reason": "First dispute."},
    ).json()["id"]

    client.patch(f"/api/appeals/{appeal_id}", json={"status": "rejected"})

    # Attempt second decision
    res2 = client.patch(
        f"/api/appeals/{appeal_id}",
        json={"status": "approved", "updated_score": 90.0},
    )
    assert res2.status_code == 400
    assert "resolved" in res2.json()["detail"].lower()
