import json
from pathlib import Path
from typing import Any, Dict, List

import app.models as models


def inject_anomalies(db_session, export_dir: Path, seed: int, scale: str) -> List[Dict[str, Any]]:
    """
    Injects exactly the four required edge cases into the dataset:
    1. Submission belongs to an unenrolled learner.
    2. Grade exceeds rubric maximum.
    3. Late penalty applied twice.
    4. Appeal changes grade without an audit history record.

    Writes ground_truth.json to export_dir with the IDs of these corrupted records.
    Labels are NOT leaked into any database columns.
    """
    anomalies: List[Dict[str, Any]] = []

    # ==============================================================
    # 1. Submission belongs to an unenrolled learner
    # ==============================================================
    submissions = (
        db_session.query(models.Submission)
        .order_by(models.Submission.id)
        .all()
    )
    target_sub = submissions[41] if len(submissions) > 42 else submissions[0]
    course_id = target_sub.assignment.course_id

    # Find a learner who is NOT enrolled in this course and has no submissions in this course
    enrolled_learner_ids = {
        e.learner_id for e in db_session.query(models.Enrollment).filter(models.Enrollment.course_id == course_id).all()
    }
    unenrolled_learners = [
        l for l in db_session.query(models.Learner).all() if l.id not in enrolled_learner_ids
    ]
    unenrolled_learner = unenrolled_learners[0]

    # Reassign this single submission to the unenrolled learner
    target_sub.learner_id = unenrolled_learner.id

    anomalies.append({
        "anomaly_id": "ANOMALY-001",
        "anomaly_type": "unenrolled_learner_submission",
        "submission_id": target_sub.id,
        "learner_id": unenrolled_learner.id,
        "assignment_id": target_sub.assignment_id,
        "course_id": course_id,
        "description": "Submission made by learner not enrolled in the assignment course",
    })

    # ==============================================================
    # 2. Grade exceeds rubric maximum
    # ==============================================================
    grades = (
        db_session.query(models.Grade)
        .order_by(models.Grade.id)
        .all()
    )
    target_grade = grades[84] if len(grades) > 85 else grades[1]

    rubric_max = 100.0
    corrupted_score = 115.0
    target_grade.raw_score = corrupted_score
    target_grade.late_penalty = 0.0
    target_grade.final_score = corrupted_score

    # Also inflate one criterion score to match raw_score
    if target_grade.criterion_scores:
        target_grade.criterion_scores[0].score += 15.0

    anomalies.append({
        "anomaly_id": "ANOMALY-002",
        "anomaly_type": "grade_exceeds_rubric_max",
        "grade_id": target_grade.id,
        "submission_id": target_grade.submission_id,
        "score": corrupted_score,
        "rubric_max": rubric_max,
        "description": "Grade final_score exceeds the rubric maximum points",
    })

    # ==============================================================
    # 3. Late penalty applied twice
    # ==============================================================
    late_grades = [
        g for g in grades
        if g.submission.is_late and g.id != target_grade.id
    ]
    if not late_grades:
        late_grades = [grades[2]]
        late_grades[0].submission.is_late = True

    target_late_grade = late_grades[0]
    raw = target_late_grade.raw_score
    expected_penalty = 10.0
    double_penalty = 20.0
    target_late_grade.late_penalty = double_penalty
    target_late_grade.final_score = max(0.0, raw - double_penalty)

    anomalies.append({
        "anomaly_id": "ANOMALY-003",
        "anomaly_type": "late_penalty_applied_twice",
        "grade_id": target_late_grade.id,
        "submission_id": target_late_grade.submission_id,
        "raw_score": raw,
        "expected_penalty": expected_penalty,
        "applied_penalty": double_penalty,
        "final_score": target_late_grade.final_score,
        "description": "Late penalty was applied twice to the grade",
    })

    # ==============================================================
    # 4. Appeal changes grade without an audit history record
    # ==============================================================
    approved_appeals = (
        db_session.query(models.Appeal)
        .filter(models.Appeal.status == "approved")
        .order_by(models.Appeal.id)
        .all()
    )
    target_appeal = approved_appeals[0]

    # Find target grade and remove any audit history logs for this grade
    appeal_sub = target_appeal.submission
    if appeal_sub and appeal_sub.grade:
        audit_grade_id = appeal_sub.grade.id
        db_session.query(models.GradeAudit).filter(
            models.GradeAudit.grade_id == audit_grade_id
        ).delete(synchronize_session=False)

    anomalies.append({
        "anomaly_id": "ANOMALY-004",
        "anomaly_type": "appeal_without_audit_history",
        "appeal_id": target_appeal.id,
        "grade_id": appeal_sub.grade.id if (appeal_sub and appeal_sub.grade) else "",
        "original_score": target_appeal.original_score,
        "updated_score": target_appeal.updated_score,
        "description": "Appeal changed grade score without an audit history log record",
    })

    db_session.commit()

    # Write ground_truth.json
    export_dir.mkdir(parents=True, exist_ok=True)
    ground_truth_path = export_dir / "ground_truth.json"
    ground_truth_payload = {
        "seed": seed,
        "scale": scale,
        "anomalies_count": len(anomalies),
        "anomalies": anomalies,
    }
    with open(ground_truth_path, "w", encoding="utf-8") as f:
        json.dump(ground_truth_payload, f, indent=2)

    return anomalies
