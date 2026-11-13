import argparse
import csv
import datetime
import json
from pathlib import Path
import random
import sqlite3
import sys

# Ensure backend directory is in path
CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, DEFAULT_DB_PATH
import app.models as models
from generator.anomaly_fixtures import inject_anomalies


# Lists for deterministic name generation
FIRST_NAMES = [
    "Aarav", "Aditi", "Amit", "Ananya", "Arun", "Bhavya", "Chetan", "Deepa",
    "Divya", "Gaurav", "Harsh", "Isha", "Kavita", "Kiran", "Madhav", "Manish",
    "Meera", "Neha", "Nikhil", "Pooja", "Pranav", "Priya", "Rahul", "Rajesh",
    "Ravi", "Riya", "Rohan", "Rohit", "Sakshi", "Sameer", "Sanjay", "Shreya",
    "Siddharth", "Sneha", "Sunil", "Suresh", "Swati", "Tanvi", "Varun", "Vikram",
    "Alexander", "Beatrix", "Charles", "Diana", "Edward", "Fiona", "George", "Helena",
    "Ian", "Julia"
]

LAST_NAMES = [
    "Agarwal", "Bose", "Chatterjee", "Chopra", "Das", "Deshmukh", "Dutta", "Gupta",
    "Iyer", "Jain", "Joshi", "Kapoor", "Kumar", "Mehta", "Mishra", "Mukherjee",
    "Nair", "Patel", "Prasad", "Rao", "Reddy", "Roy", "Sen", "Sharma", "Singh",
    "Soni", "Verma", "Yadav", "Baker", "Bennett", "Carter", "Davies", "Evans",
    "Fisher", "Gibson", "Harris", "Johnson", "Miller", "Nelson", "Parker", "Smith",
    "Taylor", "Turner", "Walker", "White", "Williams", "Wilson", "Wright", "Young", "Zimmerman"
]

COURSE_TEMPLATES = [
    ("Introduction to Computer Science", "Foundational principles of computer science and computational thinking."),
    ("Data Structures and Algorithms", "Comprehensive study of core data structures, algorithms, and complexity analysis."),
    ("Database Management Systems", "Relational algebra, SQL, database design, normalization, and ACID properties."),
    ("Software Engineering Practices", "Modern software engineering methodologies, modular design, and testing patterns."),
    ("Cloud Computing and Distributed Systems", "Architecture of distributed systems, cloud infrastructure, and microservices."),
    ("Web Application Development", "Full-stack web application development using modern protocols and standards."),
    ("Computer Networks & Protocols", "OSI model, TCP/IP stack, routing protocols, and socket programming."),
    ("Operating Systems Concepts", "Processes, threads, memory management, synchronization, and file systems."),
    ("Machine Learning Fundamentals", "Supervised, unsupervised learning, model evaluation, and feature engineering."),
    ("Cybersecurity Principles", "Cryptographic primitives, network security, authentication, and defensive engineering.")
]

ASSIGNMENT_TITLES = [
    "Syntax and Basic Control Flow",
    "Array and List Manipulations",
    "Sorting and Searching Algorithms",
    "Binary Search Tree Implementation",
    "Graph Traversal & Shortest Path",
    "Relational Schema Design & DDL",
    "Complex SQL Queries & Joins",
    "RESTful API Endpoint Development",
    "Client-Server Socket Communication",
    "Multithreaded Producer-Consumer Queue",
    "Unit Testing and Code Coverage",
    "Authentication and Token Verification",
    "Cache Layer Implementation",
    "Database Normalization Exercise",
    "Continuous Integration Pipeline Setup",
    "Asynchronous Task Processing",
    "Data Parsing and Serialization",
    "Containerized Microservice Build",
    "Web Security Vulnerability Audit",
    "Final Capstone Project Implementation"
]


def generate_data(scale: str = "starter", seed: int = 20261022, db_path: Path = DEFAULT_DB_PATH, export_dir: Path = None):
    """Main deterministic generation function."""
    rng = random.Random(seed)

    if export_dir is None:
        export_dir = BACKEND_DIR / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)

    # Determine volumes
    if scale == "full":
        num_courses = 100
        num_assignments = 1000
        num_learners = 10000
        num_submissions = 30000
    else:  # starter
        scale = "starter"
        num_courses = 5
        num_assignments = 20
        num_learners = 200
        num_submissions = 600

    print(f"=== Starting Generation [Scale: {scale}, Seed: {seed}] ===")
    print(f"Target: {num_courses} courses, {num_assignments} assignments, {num_learners} learners, {num_submissions} submissions")

    # Connect to SQLite
    engine = create_engine(
        f"sqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Create all tables cleanly
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()

    base_date = datetime.datetime(2026, 1, 1, 9, 0, 0, tzinfo=datetime.timezone.utc)

    # 1. Generate Courses
    print(f"Generating {num_courses} courses...")
    courses = []
    for i in range(1, num_courses + 1):
        tpl = COURSE_TEMPLATES[(i - 1) % len(COURSE_TEMPLATES)]
        name = f"{tpl[0]} (Sec {i})" if i > len(COURSE_TEMPLATES) else tpl[0]
        c = models.Course(
            id=f"CRS-2026-{i:06d}",
            name=name,
            description=tpl[1],
            is_active=True,
            created_at=base_date + datetime.timedelta(days=i),
        )
        courses.append(c)
        session.add(c)
    session.flush()

    # 2. Generate Learners
    print(f"Generating {num_learners} learners...")
    learners = []
    used_emails = set()
    for i in range(1, num_learners + 1):
        first = FIRST_NAMES[(i - 1) % len(FIRST_NAMES)]
        last = LAST_NAMES[((i - 1) // len(FIRST_NAMES)) % len(LAST_NAMES)]
        suffix = f"{(i - 1) // (len(FIRST_NAMES) * len(LAST_NAMES)) + 1}" if i > (len(FIRST_NAMES) * len(LAST_NAMES)) else ""
        name = f"{first} {last}"
        email = f"{first.lower()}.{last.lower()}{suffix}@example.com"
        while email in used_emails:
            email = f"{first.lower()}.{last.lower()}{rng.randint(100, 999999)}@example.com"
        used_emails.add(email)

        l = models.Learner(
            id=f"LRN-2026-{i:06d}",
            name=name,
            email=email,
            is_active=True,
            created_at=base_date + datetime.timedelta(days=i % 30),
        )
        learners.append(l)
        session.add(l)
    session.flush()

    # 3. Generate Enrollments
    # Each learner is enrolled in 1 to 3 distinct courses
    print("Generating enrollments...")
    enrollments = []
    enrollment_set = set()
    course_learners = {c.id: [] for c in courses}

    for learner in learners:
        k = min(len(courses), rng.randint(1, 3))
        selected_courses = rng.sample(courses, k)
        for c in selected_courses:
            if (c.id, learner.id) not in enrollment_set:
                enrollment_set.add((c.id, learner.id))
                e = models.Enrollment(
                    course_id=c.id,
                    learner_id=learner.id,
                    enrollment_date=c.created_at + datetime.timedelta(days=rng.randint(1, 5)),
                )
                enrollments.append(e)
                session.add(e)
                course_learners[c.id].append(learner)
    session.flush()
    print(f"Generated {len(enrollments)} enrollments.")

    # 4. Generate Assignments, Rubrics & Criteria
    print(f"Generating {num_assignments} assignments with rubrics...")
    assignments = []
    rubrics = []
    criteria = []

    for i in range(1, num_assignments + 1):
        course = courses[(i - 1) % len(courses)]
        title = ASSIGNMENT_TITLES[(i - 1) % len(ASSIGNMENT_TITLES)]
        if i > len(ASSIGNMENT_TITLES):
            title = f"{title} Part {(i - 1) // len(ASSIGNMENT_TITLES) + 1}"
        due_date = course.created_at + datetime.timedelta(days=14 + (i * 3))

        asn = models.Assignment(
            id=f"ASN-2026-{i:06d}",
            course_id=course.id,
            title=title,
            due_date=due_date,
            max_attempts=2,
            allow_resubmission=True,
            is_published=True,
        )
        assignments.append(asn)
        session.add(asn)
        session.flush()

        # Rubric (1:1 with Assignment, total_points = 100)
        rub = models.Rubric(
            id=f"RUB-2026-{i:06d}",
            assignment_id=asn.id,
            total_points=100,
        )
        rubrics.append(rub)
        session.add(rub)
        session.flush()

        # 3 Criteria summing to 100 points
        c1 = models.RubricCriterion(rubric_id=rub.id, name="Core Functional Implementation", max_marks=50)
        c2 = models.RubricCriterion(rubric_id=rub.id, name="Code Quality & Architecture", max_marks=30)
        c3 = models.RubricCriterion(rubric_id=rub.id, name="Testing & Documentation", max_marks=20)
        criteria.extend([c1, c2, c3])
        session.add_all([c1, c2, c3])

    session.flush()

    # 5. Generate Submissions (exactly num_submissions)
    print(f"Generating {num_submissions} submissions...")
    submissions = []
    submission_artifacts = []
    grades = []
    criterion_scores = []
    feedbacks = []

    subs_per_assignment = num_submissions // num_assignments
    remainder = num_submissions % num_assignments

    sub_counter = 1
    for idx, asn in enumerate(assignments):
        count = subs_per_assignment + (1 if idx < remainder else 0)
        enrolled_in_course = course_learners[asn.course_id]
        if len(enrolled_in_course) < count:
            # If not enough enrolled learners, sample with replacement or reuse
            chosen_learners = [rng.choice(enrolled_in_course) for _ in range(count)]
        else:
            chosen_learners = rng.sample(enrolled_in_course, count)

        rubric = session.query(models.Rubric).filter(models.Rubric.assignment_id == asn.id).first()
        rub_criteria = session.query(models.RubricCriterion).filter(models.RubricCriterion.rubric_id == rubric.id).order_by(models.RubricCriterion.id).all()

        for learner in chosen_learners:
            sub_id = f"SUB-2026-{sub_counter:06d}"

            # 15% late submissions
            is_late = (sub_counter % 7 == 0)
            if is_late:
                submitted_at = asn.due_date + datetime.timedelta(hours=rng.randint(2, 48))
            else:
                submitted_at = asn.due_date - datetime.timedelta(hours=rng.randint(2, 72))

            sub = models.Submission(
                id=sub_id,
                assignment_id=asn.id,
                learner_id=learner.id,
                attempt_number=1,
                submitted_at=submitted_at,
                is_late=is_late,
                status="graded",
            )
            submissions.append(sub)
            session.add(sub)
            session.flush()

            # Artifacts (1 or 2 files)
            num_art = 2 if sub_counter % 3 == 0 else 1
            art1 = models.SubmissionArtifact(
                submission_id=sub.id,
                file_name=f"solution_{sub.id.lower()}.py",
                file_type="py",
                file_size_bytes=rng.randint(1024, 15360),
                storage_path=f"/artifacts/{sub.id}/solution.py",
                uploaded_at=submitted_at,
            )
            submission_artifacts.append(art1)
            session.add(art1)
            if num_art == 2:
                art2 = models.SubmissionArtifact(
                    submission_id=sub.id,
                    file_name=f"report_{sub.id.lower()}.pdf",
                    file_type="pdf",
                    file_size_bytes=rng.randint(50000, 250000),
                    storage_path=f"/artifacts/{sub.id}/report.pdf",
                    uploaded_at=submitted_at,
                )
                submission_artifacts.append(art2)
                session.add(art2)

            # Grade & Criterion Scores
            # Criteria max: 50, 30, 20
            # Generate realistic scores (80% to 98% of max)
            s1 = round(rub_criteria[0].max_marks * rng.uniform(0.70, 0.98), 1)
            s2 = round(rub_criteria[1].max_marks * rng.uniform(0.70, 0.98), 1)
            s3 = round(rub_criteria[2].max_marks * rng.uniform(0.70, 0.98), 1)
            raw_score = round(s1 + s2 + s3, 1)

            # Standard late penalty = 10.0 points
            late_penalty = 10.0 if is_late else 0.0
            final_score = max(0.0, round(raw_score - late_penalty, 1))

            grade = models.Grade(
                id=f"GRD-2026-{sub_counter:06d}",
                submission_id=sub.id,
                raw_score=raw_score,
                late_penalty=late_penalty,
                final_score=final_score,
                is_passing=(final_score >= 60.0),
                graded_at=submitted_at + datetime.timedelta(days=2),
            )
            grades.append(grade)
            session.add(grade)
            session.flush()

            cs1 = models.CriterionScore(grade_id=grade.id, criterion_id=rub_criteria[0].id, score=s1)
            cs2 = models.CriterionScore(grade_id=grade.id, criterion_id=rub_criteria[1].id, score=s2)
            cs3 = models.CriterionScore(grade_id=grade.id, criterion_id=rub_criteria[2].id, score=s3)
            criterion_scores.extend([cs1, cs2, cs3])
            session.add_all([cs1, cs2, cs3])

            # Feedback
            tier = "Outstanding performance" if final_score >= 90 else "Solid submission" if final_score >= 80 else "Adequate work" if final_score >= 70 else "Needs improvement"
            fb = models.Feedback(
                id=f"FDB-2026-{sub_counter:06d}",
                submission_id=sub.id,
                comments=f"{tier}. Good structural alignment with requirements.",
                strengths="Clear modular logic, well documented structure.",
                improvements="Consider adding further edge case tests.",
                created_at=grade.graded_at,
            )
            feedbacks.append(fb)
            session.add(fb)

            sub_counter += 1

    session.flush()
    print(f"Generated {len(submissions)} submissions with artifacts, grades, criteria, and feedback.")

    # 6. Generate Resubmissions (~5% of submissions)
    print("Generating resubmissions...")
    resubmissions = []
    num_resubs = max(5, num_submissions // 20)
    for r_idx in range(1, num_resubs + 1):
        orig_sub = submissions[(r_idx * 7) % len(submissions)]
        # Create second attempt submission
        new_sub = models.Submission(
            id=f"SUB-2026-{(num_submissions + r_idx):06d}",
            assignment_id=orig_sub.assignment_id,
            learner_id=orig_sub.learner_id,
            attempt_number=2,
            submitted_at=orig_sub.submitted_at + datetime.timedelta(days=1),
            is_late=False,
            status="resubmitted",
        )
        session.add(new_sub)
        session.flush()

        resub = models.Resubmission(
            id=f"RSB-2026-{r_idx:06d}",
            original_submission_id=orig_sub.id,
            new_submission_id=new_sub.id,
            reason="Addressed instructor feedback on test coverage",
            requested_at=orig_sub.submitted_at + datetime.timedelta(hours=12),
        )
        resubmissions.append(resub)
        session.add(resub)
    session.flush()
    print(f"Generated {len(resubmissions)} resubmissions.")

    # 7. Generate Appeals (~3% of submissions)
    print("Generating appeals and grade audits...")
    appeals = []
    grade_audits = []
    num_appeals = max(4, num_submissions // 30)

    for a_idx in range(1, num_appeals + 1):
        sub = submissions[(a_idx * 11) % len(submissions)]
        grade = sub.grade
        orig_score = grade.final_score
        is_approved = (a_idx % 2 == 1)

        if is_approved:
            status = "approved"
            updated_score = min(100.0, round(orig_score + 6.0, 1))
            resolved_at = grade.graded_at + datetime.timedelta(days=3)

            # Update grade
            grade.final_score = updated_score
            grade.is_passing = (updated_score >= 60.0)

            # Audit history record
            audit = models.GradeAudit(
                grade_id=grade.id,
                previous_score=orig_score,
                new_score=updated_score,
                change_reason=f"Grade adjustment following appeal approval APL-2026-{a_idx:06d}",
                changed_at=resolved_at,
            )
            grade_audits.append(audit)
            session.add(audit)
        else:
            status = "rejected"
            updated_score = orig_score
            resolved_at = grade.graded_at + datetime.timedelta(days=2)

        apl = models.Appeal(
            id=f"APL-2026-{a_idx:06d}",
            submission_id=sub.id,
            learner_id=sub.learner_id,
            reason="Requesting re-evaluation of code modularity criterion.",
            status=status,
            original_score=orig_score,
            updated_score=updated_score,
            created_at=grade.graded_at + datetime.timedelta(days=1),
            resolved_at=resolved_at,
        )
        appeals.append(apl)
        session.add(apl)

    session.flush()
    session.commit()
    print(f"Generated {len(appeals)} appeals and {len(grade_audits)} audit records.")

    # ==============================================================
    # 8. Anomaly Injection
    # ==============================================================
    print("Injecting required 4 edge cases / anomalies...")
    anomalies = inject_anomalies(session, export_dir, seed=seed, scale=scale)
    print(f"Injected {len(anomalies)} anomalies successfully.")

    # ==============================================================
    # 9. Data Exports (CSV, SQL, Manifest)
    # ==============================================================
    print(f"Exporting dataset to {export_dir}...")
    export_all_data(session, engine, export_dir, scale, seed, anomalies)

    session.close()
    print("=== Data Generation and Export Complete! ===")


def export_all_data(session, engine, export_dir: Path, scale: str, seed: int, anomalies: list):
    """Exports all database tables to CSVs, a SQL seed file, and source_manifest.json."""
    tables_to_export = [
        ("courses", models.Course),
        ("learners", models.Learner),
        ("enrollments", models.Enrollment),
        ("assignments", models.Assignment),
        ("rubrics", models.Rubric),
        ("rubric_criteria", models.RubricCriterion),
        ("submissions", models.Submission),
        ("submission_artifacts", models.SubmissionArtifact),
        ("grades", models.Grade),
        ("criterion_scores", models.CriterionScore),
        ("feedback", models.Feedback),
        ("resubmissions", models.Resubmission),
        ("appeals", models.Appeal),
        ("grade_audits", models.GradeAudit),
    ]

    record_counts = {}

    # 1. Export CSVs
    for table_name, model_cls in tables_to_export:
        csv_file = export_dir / f"{table_name}.csv"
        records = session.query(model_cls).all()
        record_counts[table_name] = len(records)

        columns = [c.name for c in model_cls.__table__.columns]
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            for r in records:
                row = []
                for col in columns:
                    val = getattr(r, col)
                    if isinstance(val, datetime.datetime):
                        row.append(val.isoformat())
                    else:
                        row.append(val)
                writer.writerow(row)

    # 2. Export seed_data.sql
    sql_file = export_dir / "seed_data.sql"
    raw_conn = sqlite3.connect(engine.url.database)
    with open(sql_file, "w", encoding="utf-8") as f:
        for line in raw_conn.iterdump():
            f.write(f"{line}\n")
    raw_conn.close()

    # 3. Export source_manifest.json
    manifest_file = export_dir / "source_manifest.json"
    manifest = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "seed": seed,
        "scale": scale,
        "record_counts": record_counts,
        "anomalies_count": len(anomalies),
        "database_file": str(engine.url.database),
    }
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Exported {len(tables_to_export)} CSVs, seed_data.sql, and source_manifest.json.")


def main():
    parser = argparse.ArgumentParser(description="AssignFlow Synthetic Data Generator")
    parser.add_argument(
        "--scale",
        choices=["starter", "full"],
        default="starter",
        help="Dataset scale: starter (20 assignments, 200 learners, 600 submissions) or full (1000 assignments, 10000 learners, 30000 submissions)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20261022,
        help="Deterministic random seed (default: 20261022)",
    )
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
        help="Export directory for CSV, SQL, and manifest files",
    )

    args = parser.parse_args()
    generate_data(
        scale=args.scale,
        seed=args.seed,
        db_path=args.db_path,
        export_dir=args.export_dir,
    )


if __name__ == "__main__":
    main()
