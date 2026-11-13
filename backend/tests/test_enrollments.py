import datetime
import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError, StatementError

import app.models as models

COURSE_ID = "CRS-2026-000001"
LEARNER_ID = "LRN-2026-000001"


@pytest.fixture
def setup_active_course_and_learner(client):
    """Seed one active course and one active learner."""
    client.post(
        "/api/courses",
        json={
            "id": COURSE_ID,
            "name": "Python Fundamentals",
            "description": "Core concepts",
            "is_active": True,
        },
    )
    client.post(
        "/api/learners",
        json={
            "id": LEARNER_ID,
            "name": "Rohit Verma",
            "email": "rohit@example.com",
            "is_active": True,
        },
    )


# ==========================================
# Enrollment API Tests
# ==========================================

def test_create_valid_enrollment(client, setup_active_course_and_learner):
    """1. Create valid enrollment."""
    res = client.post(
        "/api/enrollments",
        json={"course_id": COURSE_ID, "learner_id": LEARNER_ID},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["course_id"] == COURSE_ID
    assert data["learner_id"] == LEARNER_ID
    assert "id" in data
    assert "enrollment_date" in data


def test_reject_nonexistent_course(client, setup_active_course_and_learner):
    """2. Reject nonexistent course."""
    res = client.post(
        "/api/enrollments",
        json={"course_id": "CRS-2026-999999", "learner_id": LEARNER_ID},
    )
    assert res.status_code == 404


def test_reject_nonexistent_learner(client, setup_active_course_and_learner):
    """3. Reject nonexistent learner."""
    res = client.post(
        "/api/enrollments",
        json={"course_id": COURSE_ID, "learner_id": "LRN-2026-999999"},
    )
    assert res.status_code == 404


def test_reject_duplicate_enrollment(client, setup_active_course_and_learner):
    """4. Reject duplicate enrollment."""
    res1 = client.post(
        "/api/enrollments",
        json={"course_id": COURSE_ID, "learner_id": LEARNER_ID},
    )
    assert res1.status_code == 201

    res2 = client.post(
        "/api/enrollments",
        json={"course_id": COURSE_ID, "learner_id": LEARNER_ID},
    )
    assert res2.status_code == 409


def test_reject_inactive_course(client, setup_active_course_and_learner):
    """5. Reject enrollment in inactive course."""
    client.delete(f"/api/courses/{COURSE_ID}")
    res = client.post(
        "/api/enrollments",
        json={"course_id": COURSE_ID, "learner_id": LEARNER_ID},
    )
    assert res.status_code == 400


def test_reject_inactive_learner(client, setup_active_course_and_learner):
    """6. Reject enrollment for inactive learner."""
    client.delete(f"/api/learners/{LEARNER_ID}")
    res = client.post(
        "/api/enrollments",
        json={"course_id": COURSE_ID, "learner_id": LEARNER_ID},
    )
    assert res.status_code == 400


def test_verify_foreign_key_enforcement(db_session):
    """7. Verify foreign-key enforcement in SQLite."""
    enrollment = models.Enrollment(
        course_id="CRS-2026-999999",
        learner_id="LRN-2026-999999",
    )
    db_session.add(enrollment)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# ==========================================
# Database Constraints & Model Tests
# ==========================================

def test_db_all_six_tables_created(db_session):
    """Database Test 1: All six tables exist in the schema."""
    inspector = inspect(db_session.bind)
    tables = set(inspector.get_table_names())
    expected_tables = {
        "courses",
        "learners",
        "enrollments",
        "assignments",
        "rubrics",
        "rubric_criteria",
    }
    assert expected_tables.issubset(tables)


def test_db_primary_keys(db_session):
    """Database Test 2: Primary keys prevent duplicate insertions."""
    course1 = models.Course(id="CRS-2026-000001", name="Course 1")
    db_session.add(course1)
    db_session.commit()
    db_session.expunge(course1)

    course2 = models.Course(id="CRS-2026-000001", name="Course 2 Duplicate PK")
    db_session.add(course2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_db_foreign_keys(db_session):
    """Database Test 3: Foreign keys reject invalid references."""
    assignment = models.Assignment(
        id="ASN-2026-000001",
        course_id="CRS-2026-NONEXISTENT",
        title="Assignment 1",
        due_date=datetime.datetime.now(datetime.timezone.utc),
    )
    db_session.add(assignment)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_db_enrollment_unique_constraint(db_session):
    """Database Test 4: Enrollment composite unique constraint works."""
    course = models.Course(id="CRS-2026-000001", name="Course 1")
    learner = models.Learner(id="LRN-2026-000001", name="Learner 1", email="l1@test.com")
    db_session.add_all([course, learner])
    db_session.commit()

    e1 = models.Enrollment(course_id="CRS-2026-000001", learner_id="LRN-2026-000001")
    db_session.add(e1)
    db_session.commit()

    e2 = models.Enrollment(course_id="CRS-2026-000001", learner_id="LRN-2026-000001")
    db_session.add(e2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_db_rubric_assignment_unique_constraint(db_session):
    """Database Test 5: Rubric assignment unique constraint (one rubric per assignment)."""
    course = models.Course(id="CRS-2026-000001", name="Course 1")
    assignment = models.Assignment(
        id="ASN-2026-000001",
        course_id="CRS-2026-000001",
        title="Assignment 1",
        due_date=datetime.datetime.now(datetime.timezone.utc),
    )
    db_session.add_all([course, assignment])
    db_session.commit()

    r1 = models.Rubric(id="RUB-001", assignment_id="ASN-2026-000001", total_points=100)
    db_session.add(r1)
    db_session.commit()

    r2 = models.Rubric(id="RUB-002", assignment_id="ASN-2026-000001", total_points=100)
    db_session.add(r2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_db_numerical_check_constraints(db_session):
    """Database Test 6: Numerical CheckConstraints work."""
    course = models.Course(id="CRS-2026-000001", name="Course 1")
    db_session.add(course)
    db_session.commit()

    # 1. Assignment max_attempts < 1 rejected
    a_bad_attempts = models.Assignment(
        id="ASN-2026-000001",
        course_id="CRS-2026-000001",
        title="Bad Attempts",
        due_date=datetime.datetime.now(datetime.timezone.utc),
        max_attempts=0,
    )
    db_session.add(a_bad_attempts)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # 2. Assignment allow_resubmission is False but max_attempts > 1 rejected
    a_bad_resubmission = models.Assignment(
        id="ASN-2026-000002",
        course_id="CRS-2026-000001",
        title="Bad Resubmission",
        due_date=datetime.datetime.now(datetime.timezone.utc),
        allow_resubmission=False,
        max_attempts=2,
    )
    db_session.add(a_bad_resubmission)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Valid Assignment
    a_valid = models.Assignment(
        id="ASN-2026-000003",
        course_id="CRS-2026-000001",
        title="Valid Assignment",
        due_date=datetime.datetime.now(datetime.timezone.utc),
        allow_resubmission=True,
        max_attempts=3,
    )
    db_session.add(a_valid)
    db_session.commit()

    # 3. Rubric total_points <= 0 rejected
    rubric_bad = models.Rubric(id="RUB-003", assignment_id="ASN-2026-000003", total_points=0)
    db_session.add(rubric_bad)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Valid Rubric
    rubric_valid = models.Rubric(id="RUB-004", assignment_id="ASN-2026-000003", total_points=100)
    db_session.add(rubric_valid)
    db_session.commit()

    # 4. RubricCriterion max_marks <= 0 rejected
    crit_bad = models.RubricCriterion(rubric_id="RUB-004", name="Criterion 1", max_marks=0)
    db_session.add(crit_bad)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_db_utc_timestamps_roundtrip(db_session):
    """Database Test 7: UTC timestamps round-trip correctly with timezone info restored."""
    fixed_time = datetime.datetime(2026, 11, 13, 12, 0, 0, tzinfo=datetime.timezone.utc)
    course = models.Course(id="CRS-2026-000001", name="Course 1", created_at=fixed_time)
    db_session.add(course)
    db_session.commit()

    fetched = db_session.query(models.Course).filter(models.Course.id == "CRS-2026-000001").first()
    assert fetched.created_at is not None
    assert fetched.created_at.tzinfo == datetime.timezone.utc
    assert fetched.created_at == fixed_time


def test_db_reject_naive_timestamps(db_session):
    """Database Test 8: Naive timestamps are rejected where required."""
    naive_time = datetime.datetime(2026, 11, 13, 12, 0, 0)  # No tzinfo
    course = models.Course(id="CRS-2026-000001", name="Course 1", created_at=naive_time)
    db_session.add(course)
    with pytest.raises(StatementError):
        db_session.commit()
    db_session.rollback()
