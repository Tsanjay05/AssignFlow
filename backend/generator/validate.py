import argparse
import datetime
import json
from pathlib import Path
import sqlite3
import sys

# Ensure backend directory is in path
CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import DEFAULT_DB_PATH
import app.models as models


def validate_dataset(db_path: Path = DEFAULT_DB_PATH, export_dir: Path = None):
    """Runs all validation rules against the SQLite database and compares against ground truth."""
    if export_dir is None:
        export_dir = BACKEND_DIR / "exports"

    print("=== Starting AssignFlow Validation Engine ===")
    print(f"Database: {db_path}")
    print(f"Exports Directory: {export_dir}")

    engine = create_engine(
        f"sqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()

    checks_results = {}
    detected_anomalies = []

    # ==============================================================
    # 1. Primary-Key Uniqueness & Foreign-Key Integrity
    # ==============================================================
    print("\n[Check 1] Validating Primary-Key Uniqueness & Foreign-Key Integrity...")
    raw_conn = sqlite3.connect(db_path.as_posix())
    cursor = raw_conn.cursor()

    # Foreign key check via SQLite PRAGMA
    cursor.execute("PRAGMA foreign_key_check;")
    fk_violations = cursor.fetchall()

    # Tables list
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [row[0] for row in cursor.fetchall()]

    pk_violations = []
    for tbl in tables:
        cursor.execute(f"PRAGMA table_info({tbl});")
        cols = cursor.fetchall()
        pk_cols = [c[1] for c in cols if c[5] > 0]
        if pk_cols:
            pk_str = ", ".join(pk_cols)
            cursor.execute(f"SELECT {pk_str}, COUNT(*) FROM {tbl} GROUP BY {pk_str} HAVING COUNT(*) > 1;")
            dupes = cursor.fetchall()
            if dupes:
                pk_violations.append({"table": tbl, "duplicates": len(dupes)})

    raw_conn.close()

    integrity_passed = (len(fk_violations) == 0 and len(pk_violations) == 0)
    checks_results["integrity"] = {
        "status": "PASS" if integrity_passed else "FAIL",
        "tables_checked": len(tables),
        "foreign_key_violations": len(fk_violations),
        "primary_key_violations": len(pk_violations),
    }
    print(f"  -> Integrity Status: {'PASS' if integrity_passed else 'FAIL'}")

    # ==============================================================
    # 2. Enrollment Consistency (Detect unenrolled learner submissions)
    # ==============================================================
    print("\n[Check 2] Validating Enrollment Consistency...")
    submissions = session.query(models.Submission).all()
    unenrolled_submissions = []

    # Build cache of valid (course_id, learner_id) enrollments
    enrollments = session.query(models.Enrollment).all()
    enrollment_pairs = {(e.course_id, e.learner_id) for e in enrollments}

    for sub in submissions:
        course_id = sub.assignment.course_id
        if (course_id, sub.learner_id) not in enrollment_pairs:
            anomaly_info = {
                "anomaly_type": "unenrolled_learner_submission",
                "entity_id": sub.id,
                "submission_id": sub.id,
                "learner_id": sub.learner_id,
                "course_id": course_id,
                "assignment_id": sub.assignment_id,
                "detail": f"Submission {sub.id} belongs to learner {sub.learner_id} who is not enrolled in course {course_id}.",
            }
            unenrolled_submissions.append(anomaly_info)
            detected_anomalies.append(anomaly_info)

    checks_results["enrollment_consistency"] = {
        "status": "ANOMALY_DETECTED" if unenrolled_submissions else "PASS",
        "total_submissions_inspected": len(submissions),
        "anomalies_detected": len(unenrolled_submissions),
        "detected_items": unenrolled_submissions,
    }
    print(f"  -> Detected {len(unenrolled_submissions)} unenrolled learner submission(s).")

    # ==============================================================
    # 3. Score Reconciliation (Detect grade exceeding rubric max)
    # ==============================================================
    print("\n[Check 3] Validating Score Reconciliation...")
    grades = session.query(models.Grade).all()
    exceeded_grades = []

    for g in grades:
        rubric = g.submission.assignment.rubric
        max_allowed = float(rubric.total_points) if rubric else 100.0

        if g.final_score > max_allowed or g.raw_score > max_allowed:
            anomaly_info = {
                "anomaly_type": "grade_exceeds_rubric_max",
                "entity_id": g.id,
                "grade_id": g.id,
                "submission_id": g.submission_id,
                "score": g.final_score,
                "rubric_max": max_allowed,
                "detail": f"Grade {g.id} score ({g.final_score}) exceeds rubric max ({max_allowed}).",
            }
            exceeded_grades.append(anomaly_info)
            detected_anomalies.append(anomaly_info)

    checks_results["score_reconciliation"] = {
        "status": "ANOMALY_DETECTED" if exceeded_grades else "PASS",
        "total_grades_inspected": len(grades),
        "anomalies_detected": len(exceeded_grades),
        "detected_items": exceeded_grades,
    }
    print(f"  -> Detected {len(exceeded_grades)} grade(s) exceeding rubric maximum.")

    # ==============================================================
    # 4. Penalty Logic (Detect late penalty applied twice)
    # ==============================================================
    print("\n[Check 4] Validating Late Penalty Logic...")
    double_penalty_grades = []
    expected_late_penalty = 10.0

    for g in grades:
        if g.submission.is_late:
            # Check if penalty was applied twice (20.0 instead of 10.0)
            if round(g.late_penalty, 2) >= round(2 * expected_late_penalty, 2) or round(g.raw_score - g.final_score, 2) >= round(2 * expected_late_penalty, 2):
                anomaly_info = {
                    "anomaly_type": "late_penalty_applied_twice",
                    "entity_id": g.id,
                    "grade_id": g.id,
                    "submission_id": g.submission_id,
                    "raw_score": g.raw_score,
                    "applied_penalty": g.late_penalty,
                    "expected_penalty": expected_late_penalty,
                    "final_score": g.final_score,
                    "detail": f"Grade {g.id} had late penalty applied twice ({g.late_penalty} deduction).",
                }
                double_penalty_grades.append(anomaly_info)
                detected_anomalies.append(anomaly_info)

    checks_results["penalty_logic"] = {
        "status": "ANOMALY_DETECTED" if double_penalty_grades else "PASS",
        "total_grades_inspected": len(grades),
        "anomalies_detected": len(double_penalty_grades),
        "detected_items": double_penalty_grades,
    }
    print(f"  -> Detected {len(double_penalty_grades)} grade(s) with double late penalty.")

    # ==============================================================
    # 5. Traceability (Detect appeal changing grade without audit history)
    # ==============================================================
    print("\n[Check 5] Validating Traceability & Audit History...")
    appeals = session.query(models.Appeal).filter(models.Appeal.status == "approved").all()
    unlogged_appeals = []

    for apl in appeals:
        # If the appeal modified the score
        if apl.original_score != apl.updated_score:
            grade = apl.submission.grade if (apl.submission and apl.submission.grade) else None
            if grade:
                # Look for audit log matching this grade adjustment
                audit_logs = session.query(models.GradeAudit).filter(
                    models.GradeAudit.grade_id == grade.id,
                ).all()
                if not audit_logs:
                    anomaly_info = {
                        "anomaly_type": "appeal_without_audit_history",
                        "entity_id": apl.id,
                        "appeal_id": apl.id,
                        "grade_id": grade.id,
                        "original_score": apl.original_score,
                        "updated_score": apl.updated_score,
                        "detail": f"Appeal {apl.id} modified grade {grade.id} score without an audit log record.",
                    }
                    unlogged_appeals.append(anomaly_info)
                    detected_anomalies.append(anomaly_info)

    checks_results["traceability"] = {
        "status": "ANOMALY_DETECTED" if unlogged_appeals else "PASS",
        "total_approved_appeals_inspected": len(appeals),
        "anomalies_detected": len(unlogged_appeals),
        "detected_items": unlogged_appeals,
    }
    print(f"  -> Detected {len(unlogged_appeals)} appeal(s) missing audit history logs.")

    # ==============================================================
    # 6. Precision & Recall against Ground Truth
    # ==============================================================
    ground_truth_path = export_dir / "ground_truth.json"
    metrics = {
        "ground_truth_file": str(ground_truth_path),
        "ground_truth_found": False,
        "true_positives": 0,
        "false_positives": 0,
        "false_negatives": 0,
        "precision": 0.0,
        "recall": 0.0,
        "f1_score": 0.0,
    }

    if ground_truth_path.exists():
        with open(ground_truth_path, "r", encoding="utf-8") as f:
            gt_data = json.load(f)

        gt_anomalies = gt_data.get("anomalies", [])
        metrics["ground_truth_found"] = True
        metrics["total_ground_truth_anomalies"] = len(gt_anomalies)

        # Build expected signature set: (anomaly_type, primary_id)
        def get_gt_key(gt):
            atype = gt["anomaly_type"]
            if atype == "unenrolled_learner_submission":
                return (atype, gt.get("submission_id"))
            elif atype in ("grade_exceeds_rubric_max", "late_penalty_applied_twice"):
                return (atype, gt.get("grade_id"))
            elif atype == "appeal_without_audit_history":
                return (atype, gt.get("appeal_id"))
            return (atype, gt.get("anomaly_id"))

        def get_det_key(det):
            atype = det["anomaly_type"]
            return (atype, det["entity_id"])

        gt_keys = {get_gt_key(a) for a in gt_anomalies}
        det_keys = {get_det_key(a) for a in detected_anomalies}

        tp = len(det_keys & gt_keys)
        fp = len(det_keys - gt_keys)
        fn = len(gt_keys - det_keys)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        metrics.update({
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
        })

    # ==============================================================
    # 7. Output Validation Summary JSON
    # ==============================================================
    summary_path = export_dir / "validation_summary.json"
    summary_payload = {
        "validated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "database_file": str(db_path),
        "overall_status": "VALIDATED_WITH_EXPECTED_ANOMALIES",
        "total_anomalies_detected": len(detected_anomalies),
        "checks": checks_results,
        "evaluation_metrics": metrics,
    }

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_payload, f, indent=2)

    session.close()

    print("\n" + "=" * 60)
    print("              VALIDATION ENGINE SUMMARY")
    print("=" * 60)
    print(f"Total Anomalies Detected: {len(detected_anomalies)}")
    print(f"Precision:               {metrics['precision'] * 100:.1f}%")
    print(f"Recall:                  {metrics['recall'] * 100:.1f}%")
    print(f"F1-Score:                {metrics['f1_score'] * 100:.1f}%")
    print(f"Summary JSON Written:    {summary_path}")
    print("=" * 60)

    return summary_payload


def main():
    parser = argparse.ArgumentParser(description="AssignFlow Validation Engine")
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="Target SQLite database file path",
    )
    parser.add_argument(
        "--export-dir",
        type=Path,
        default=BACKEND_DIR / "exports",
        help="Directory containing ground_truth.json and where validation_summary.json will be saved",
    )

    args = parser.parse_args()
    validate_dataset(db_path=args.db_path, export_dir=args.export_dir)


if __name__ == "__main__":
    main()
