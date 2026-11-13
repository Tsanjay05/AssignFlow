# AssignFlow – Assignment Management & Evaluation Platform

AssignFlow is an enterprise-grade Assignment Management and Evaluation Platform engineered to handle academic lifecycles with strict traceability, robust data integrity, and high-performance workflow execution. It provides complete end-to-end lifecycle coverage—from course master data modeling and assignment publication through multi-artifact learner submissions, rubric-based evaluation, resubmission governance, grade appeals, and immutable auditing.

---

## 1. Project Overview

In academic and enterprise learning environments, managing student submissions, grading consistency, late policies, and appeal audit trails requires high fidelity and strict relational integrity. **AssignFlow** bridges institutional administrative governance with an intuitive educator and learner workflow. The platform enforces business constraints at the database, schema, and API levels while exposing an operations dashboard for real-time visibility into performance KPIs and validation anomalies.

---

## 2. Features & Workflows

AssignFlow orchestrates six core functional workflows:

### A. Master Data Management
- Hierarchical course management with unique course codes and credit allocations.
- Learner profiles with email uniqueness and enrollment lifecycle tracking.
- Many-to-many enrollment modeling with unique compound constraints (`course_id`, `learner_id`) preventing duplicate enrollments.

### B. Assignment Publication Workflow
- Assignments created in `DRAFT` status and can only transition to `PUBLISHED` once an associated rubric with evaluation criteria is attached and a valid future due date is configured.
- Configurable maximum attempt thresholds, late submission policies, and late penalty percentage deductions.
- Native UTC timezone-aware validation using custom SQLite `UTCDateTime` type decorators.

### C. Learner Submission Workflow
- Strict enrollment gating: Submissions are rejected with `403 Forbidden` if the learner is not actively enrolled in the course.
- Multi-file artifact support with mime-type, file size, and file path tracking.
- Automatic late detection comparing submission timestamps against assignment deadlines in UTC.
- Enforced attempt counting with unique compound constraints (`assignment_id`, `learner_id`, `attempt_number`) preventing exceeding `max_attempts`.

### D. Rubric-Based Grading & Feedback
- Multi-criteria rubric evaluation where criterion scores are validated against criterion maximums (`max_marks`).
- Automatic calculation of raw scores as the sum of criterion marks.
- Deterministic, one-time application of late penalty deductions if the submission was flagged as late.
- Rich qualitative feedback capture (strengths, areas for improvement, general comments).

### E. Resubmissions & Appeals
- Structured resubmission request and approval workflow ensuring submission limits are honored.
- Grade appeal lifecycle (`PENDING` -> `APPROVED` / `REJECTED`) with decision rationale tracking.

### F. Immutable Grade Auditing
- Every grade revision resulting from an approved appeal automatically generates an immutable `GradeAudit` record capturing old score, new score, evaluator/reviewer identity, change reason, and UTC timestamp.

---

## 3. Architecture & Tech Stack

The platform is designed around clean architectural separation between the presentation tier, REST API layer, relational ORM, and validation engine:

```text
C:\CandidateWorkspace\
│
├── backend\
│   ├── app\
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI application, routing, and business logic
│   │   ├── models.py            # SQLAlchemy ORM models (14 entities & bridge tables)
│   │   ├── schemas.py           # Pydantic v2 schemas and request/response models
│   │   └── database.py          # SQLite engine, UTCDateTime decorator, SessionLocal
│   ├── generator\
│   │   ├── __init__.py
│   │   ├── generate.py          # Deterministic synthetic data generator
│   │   ├── anomaly_fixtures.py  # Isolated negative edge-case fixtures
│   │   └── validate.py          # Data integrity and anomaly detection engine
│   ├── exports\                 # CSV, JSON manifests, and seed_data.sql outputs
│   ├── tests\                   # Automated pytest suites (51 unit tests)
│   └── requirements.txt         # Pinned Python package dependencies
│
├── frontend\
│   ├── index.html               # Responsive dashboard UI (Tailwind CSS)
│   └── app.js                   # Asynchronous API integration and DOM controller
│
└── README.md                    # Project documentation
```

### Technology Highlights
- **Backend Framework:** [FastAPI](https://fastapi.tiangolo.com/) (0.110.0) with [Uvicorn](https://www.uvicorn.org/) (0.27.1) ASGI server.
- **ORM & Database:** [SQLAlchemy](https://www.sqlalchemy.org/) (2.0.28) over [SQLite](https://www.sqlite.org/) with enforced foreign key pragmas (`PRAGMA foreign_keys = ON`).
- **Data Validation:** [Pydantic](https://docs.pydantic.dev/) v2 (2.6.3) with strict field validations, regex constraints, and UTC timezone converters.
- **Testing:** [Pytest](https://docs.pytest.org/) (8.0.2) with [HTTPX](https://www.python-httpx.org/) (0.27.0) TestClient.
- **Frontend:** Vanilla modern JavaScript (ES6+ async/await) and HTML5 styled with [Tailwind CSS](https://tailwindcss.com/) CDN.

---

## 4. Data Engineering & Edge Cases

AssignFlow includes a production-grade synthetic data generation engine located in `backend/generator/generate.py`.

### Determinism & Reproducibility
- Configurable scale parameters:
  - **`starter` Scale:** 20 assignments, 200 learners, 600 submissions, 14 relational tables.
  - **`full` Scale:** 1,000 assignments, 10,000 learners, 30,000 submissions.
- Powered by a fixed seed (`20261022`) using Python's `random.Random(seed)` to guarantee bit-for-bit identical outputs across environments.
- Exports relational data to 14 standard CSV files, an automated SQL seed file (`backend/exports/seed_data.sql`), and manifest files (`source_manifest.json`, `ground_truth.json`).

### Injected Edge Cases (Negative Scenarios)
Four specific anomalies are deterministically injected via `backend/generator/anomaly_fixtures.py` into the dataset to test anomaly detection and validation routines without label leakage:

1. **Unenrolled Learner Submission (`SUB-2026-000042`):**
   - Learner `LRN-2026-000001` submitted work for an assignment in course `CRS-2026-000002` where no valid enrollment record exists.
2. **Grade Exceeds Rubric Maximum (`GRD-2026-000085`):**
   - A grade was assigned `115.0` points where the associated rubric maximum point ceiling is `100.0`.
3. **Late Penalty Applied Twice (`GRD-2026-000007`):**
   - A 10% late penalty was deducted twice (`20.0` points deducted instead of `10.0`), dropping the final score to `80.0`.
4. **Appeal Grade Revision Without Audit History (`APL-2026-000001`):**
   - An appeal resulted in a score modification on grade `GRD-2026-000003` from `84.8` to `90.8`, but the corresponding immutable `GradeAudit` event record was omitted.

The validation script `backend/generator/validate.py` inspects the database and achieves 100% precision and recall against these injected cases.

---

## 5. Setup & Installation

### Prerequisites
- Python 3.10+ (tested on Python 3.12)
- Modern Web Browser (Chrome, Firefox, Edge)

### Step 1: Navigate to the Workspace
```powershell
cd C:\CandidateWorkspace
```

### Step 2: Create and Activate Virtual Environment
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Step 3: Install Dependencies
```powershell
pip install -r requirements.txt
```

---

## 6. Running the Application

### Start Backend API Server (Port 8000)
From the `C:\CandidateWorkspace\backend` directory with the virtual environment activated:
```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- Interactive API Documentation (Swagger UI): [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- API Health Check: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### Start Frontend Dashboard (Port 3000)
Open a separate PowerShell terminal:
```powershell
cd C:\CandidateWorkspace\frontend
python -m http.server 3000
```
- Web Application URL: [http://127.0.0.1:3000](http://127.0.0.1:3000)

---

## 7. Generating Synthetic Data

To generate fresh deterministic synthetic data and populate the database:

### Generate Data (Starter Scale)
From the `C:\CandidateWorkspace\backend` directory:
```powershell
python generator/generate.py --scale starter --seed 20261022
```

### Validate Data & Detect Anomalies
To execute the validation engine and verify database integrity and anomalies:
```powershell
python generator/validate.py
```
This produces `backend/exports/validation_summary.json` containing anomaly detection results, rule counts, and ground-truth precision/recall statistics.

---

## 8. Testing

Execute the comprehensive automated test suite across all modules:
```powershell
cd C:\CandidateWorkspace\backend
pytest tests -v
```

### Test Suite Coverage:
- `tests/test_courses.py` – Course CRUD, unique code constraint, validation.
- `tests/test_learners.py` – Learner CRUD, email uniqueness, schema validation.
- `tests/test_enrollments.py` – Duplicate prevention, active enrollment status checks.
- `tests/test_assignments.py` – Drafting, rubric attachment, publication gating, max attempts.
- `tests/test_submissions.py` – Enrollment enforcement, late detection, artifact uploads.
- `tests/test_grading.py` – Rubric criteria score bounding, late penalty calculation, feedback.
- `tests/test_appeals.py` – Appeal submission, review workflow, immutable grade audit creation.
