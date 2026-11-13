from contextlib import asynccontextmanager
import datetime
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
import app.models as models
import app.schemas as schemas


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on application startup
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="AssignFlow API",
    description="Assignment Management & Evaluation Platform API",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS to allow the frontend to communicate with the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handler for database integrity errors
@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "Database integrity violation. Duplicate or invalid reference."},
    )


# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "ok", "message": "AssignFlow Backend is running."}


# ==========================================
# Course Endpoints
# ==========================================

@app.post(
    "/api/courses",
    response_model=schemas.CourseResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Courses"],
)
def create_course(
    course_in: schemas.CourseCreate,
    db: Session = Depends(get_db),
):
    existing = db.query(models.Course).filter(models.Course.id == course_in.id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Course with ID '{course_in.id}' already exists.",
        )

    db_course = models.Course(
        id=course_in.id,
        name=course_in.name,
        description=course_in.description,
        is_active=course_in.is_active,
    )
    try:
        db.add(db_course)
        db.commit()
        db.refresh(db_course)
        return db_course
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Course with ID '{course_in.id}' already exists.",
        )


@app.get(
    "/api/courses",
    response_model=List[schemas.CourseResponse],
    tags=["Courses"],
)
def list_courses(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max number of records to return"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
):
    query = db.query(models.Course)
    if is_active is not None:
        query = query.filter(models.Course.is_active == is_active)
    return query.order_by(models.Course.id).offset(skip).limit(limit).all()


@app.get(
    "/api/courses/{course_id}",
    response_model=schemas.CourseResponse,
    tags=["Courses"],
)
def get_course(
    course_id: str,
    db: Session = Depends(get_db),
):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course '{course_id}' not found.",
        )
    return course


@app.patch(
    "/api/courses/{course_id}",
    response_model=schemas.CourseResponse,
    tags=["Courses"],
)
def update_course(
    course_id: str,
    course_in: schemas.CourseUpdate,
    db: Session = Depends(get_db),
):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course '{course_id}' not found.",
        )

    update_data = course_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(course, field, value)

    try:
        db.commit()
        db.refresh(course)
        return course
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Update failed due to a database integrity conflict.",
        )


@app.delete(
    "/api/courses/{course_id}",
    tags=["Courses"],
)
def deactivate_course(
    course_id: str,
    db: Session = Depends(get_db),
):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course '{course_id}' not found.",
        )

    if not course.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Course '{course_id}' is already deactivated.",
        )

    course.is_active = False
    db.commit()
    db.refresh(course)
    return {
        "message": f"Course '{course_id}' deactivated successfully.",
        "id": course_id,
        "is_active": False,
    }


# ==========================================
# Learner Endpoints
# ==========================================

@app.post(
    "/api/learners",
    response_model=schemas.LearnerResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Learners"],
)
def create_learner(
    learner_in: schemas.LearnerCreate,
    db: Session = Depends(get_db),
):
    existing_id = db.query(models.Learner).filter(models.Learner.id == learner_in.id).first()
    if existing_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Learner with ID '{learner_in.id}' already exists.",
        )

    existing_email = db.query(models.Learner).filter(models.Learner.email == learner_in.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Learner with email '{learner_in.email}' already exists.",
        )

    db_learner = models.Learner(
        id=learner_in.id,
        name=learner_in.name,
        email=learner_in.email,
        is_active=learner_in.is_active,
    )
    try:
        db.add(db_learner)
        db.commit()
        db.refresh(db_learner)
        return db_learner
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Learner ID or email already exists.",
        )


@app.get(
    "/api/learners",
    response_model=List[schemas.LearnerResponse],
    tags=["Learners"],
)
def list_learners(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max number of records to return"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
):
    query = db.query(models.Learner)
    if is_active is not None:
        query = query.filter(models.Learner.is_active == is_active)
    return query.order_by(models.Learner.id).offset(skip).limit(limit).all()


@app.get(
    "/api/learners/{learner_id}",
    response_model=schemas.LearnerResponse,
    tags=["Learners"],
)
def get_learner(
    learner_id: str,
    db: Session = Depends(get_db),
):
    learner = db.query(models.Learner).filter(models.Learner.id == learner_id).first()
    if not learner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Learner '{learner_id}' not found.",
        )
    return learner


@app.patch(
    "/api/learners/{learner_id}",
    response_model=schemas.LearnerResponse,
    tags=["Learners"],
)
def update_learner(
    learner_id: str,
    learner_in: schemas.LearnerUpdate,
    db: Session = Depends(get_db),
):
    learner = db.query(models.Learner).filter(models.Learner.id == learner_id).first()
    if not learner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Learner '{learner_id}' not found.",
        )

    update_data = learner_in.model_dump(exclude_unset=True)
    if "email" in update_data:
        duplicate_email = (
            db.query(models.Learner)
            .filter(
                models.Learner.email == update_data["email"],
                models.Learner.id != learner_id,
            )
            .first()
        )
        if duplicate_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Learner with email '{update_data['email']}' already exists.",
            )

    for field, value in update_data.items():
        setattr(learner, field, value)

    try:
        db.commit()
        db.refresh(learner)
        return learner
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Update failed due to a database integrity conflict.",
        )


@app.delete(
    "/api/learners/{learner_id}",
    tags=["Learners"],
)
def deactivate_learner(
    learner_id: str,
    db: Session = Depends(get_db),
):
    learner = db.query(models.Learner).filter(models.Learner.id == learner_id).first()
    if not learner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Learner '{learner_id}' not found.",
        )

    if not learner.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Learner '{learner_id}' is already deactivated.",
        )

    learner.is_active = False
    db.commit()
    db.refresh(learner)
    return {
        "message": f"Learner '{learner_id}' deactivated successfully.",
        "id": learner_id,
        "is_active": False,
    }


# ==========================================
# Enrollment Endpoints
# ==========================================

@app.post(
    "/api/enrollments",
    response_model=schemas.EnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Enrollments"],
)
def create_enrollment(
    enrollment_in: schemas.EnrollmentCreate,
    db: Session = Depends(get_db),
):
    # Verify course exists
    course = db.query(models.Course).filter(models.Course.id == enrollment_in.course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course '{enrollment_in.course_id}' not found.",
        )

    # Verify learner exists
    learner = db.query(models.Learner).filter(models.Learner.id == enrollment_in.learner_id).first()
    if not learner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Learner '{enrollment_in.learner_id}' not found.",
        )

    # Verify course is active
    if not course.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot enroll in inactive course '{course.id}'.",
        )

    # Verify learner is active
    if not learner.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot enroll inactive learner '{learner.id}'.",
        )

    # Check for duplicate enrollment
    existing_enrollment = (
        db.query(models.Enrollment)
        .filter(
            models.Enrollment.course_id == enrollment_in.course_id,
            models.Enrollment.learner_id == enrollment_in.learner_id,
        )
        .first()
    )
    if existing_enrollment:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Learner '{learner.id}' is already enrolled in course '{course.id}'.",
        )

    enrollment_date = enrollment_in.enrollment_date or datetime.datetime.now(datetime.timezone.utc)

    db_enrollment = models.Enrollment(
        course_id=enrollment_in.course_id,
        learner_id=enrollment_in.learner_id,
        enrollment_date=enrollment_date,
    )
    try:
        db.add(db_enrollment)
        db.commit()
        db.refresh(db_enrollment)
        return db_enrollment
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate enrollment or foreign-key constraint violation.",
        )


@app.get(
    "/api/enrollments",
    response_model=List[schemas.EnrollmentResponse],
    tags=["Enrollments"],
)
def list_enrollments(
    course_id: Optional[str] = Query(None, description="Filter by course ID"),
    learner_id: Optional[str] = Query(None, description="Filter by learner ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max number of records to return"),
    db: Session = Depends(get_db),
):
    query = db.query(models.Enrollment)
    if course_id is not None:
        query = query.filter(models.Enrollment.course_id == course_id)
    if learner_id is not None:
        query = query.filter(models.Enrollment.learner_id == learner_id)
    return query.order_by(models.Enrollment.id).offset(skip).limit(limit).all()


# ==========================================
# Assignment Endpoints
# ==========================================

@app.post(
    "/api/assignments",
    response_model=schemas.Assignment,
    status_code=status.HTTP_201_CREATED,
    tags=["Assignments"],
)
def create_assignment(
    assignment_in: schemas.AssignmentCreate,
    db: Session = Depends(get_db),
):
    course = db.query(models.Course).filter(models.Course.id == assignment_in.course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course '{assignment_in.course_id}' not found.",
        )

    # Determine ID
    if assignment_in.id:
        existing = db.query(models.Assignment).filter(models.Assignment.id == assignment_in.id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Assignment with ID '{assignment_in.id}' already exists.",
            )
        assignment_id = assignment_in.id
    else:
        count = db.query(models.Assignment).count() + 1
        assignment_id = f"ASN-2026-{count:06d}"
        while db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first():
            count += 1
            assignment_id = f"ASN-2026-{count:06d}"

    db_assignment = models.Assignment(
        id=assignment_id,
        course_id=assignment_in.course_id,
        title=assignment_in.title,
        due_date=assignment_in.due_date,
        max_attempts=assignment_in.max_attempts,
        allow_resubmission=assignment_in.allow_resubmission,
        is_published=False,
    )
    db.add(db_assignment)
    db.flush()

    if assignment_in.rubric:
        rubric_in = assignment_in.rubric
        rubric_id = rubric_in.id or f"RUB-2026-{assignment_id.split('-')[-1]}"
        db_rubric = models.Rubric(
            id=rubric_id,
            assignment_id=db_assignment.id,
            total_points=rubric_in.total_points,
        )
        db.add(db_rubric)
        db.flush()

        for crit in rubric_in.criteria:
            db_crit = models.RubricCriterion(
                rubric_id=db_rubric.id,
                name=crit.name,
                max_marks=crit.max_marks,
            )
            db.add(db_crit)

    try:
        db.commit()
        db.refresh(db_assignment)
        return db_assignment
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assignment creation failed due to an integrity constraint violation.",
        )


@app.get(
    "/api/assignments",
    response_model=List[schemas.Assignment],
    tags=["Assignments"],
)
def list_assignments(
    course_id: Optional[str] = Query(None, description="Filter by course ID"),
    is_published: Optional[bool] = Query(None, description="Filter by published status"),
    skip: int = Query(0, ge=0, description="Records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max records to return"),
    db: Session = Depends(get_db),
):
    query = db.query(models.Assignment)
    if course_id is not None:
        query = query.filter(models.Assignment.course_id == course_id)
    if is_published is not None:
        query = query.filter(models.Assignment.is_published == is_published)
    return query.order_by(models.Assignment.id).offset(skip).limit(limit).all()


@app.get(
    "/api/assignments/{assignment_id}",
    response_model=schemas.Assignment,
    tags=["Assignments"],
)
def get_assignment(
    assignment_id: str,
    db: Session = Depends(get_db),
):
    assignment = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assignment '{assignment_id}' not found.",
        )
    return assignment


@app.post(
    "/api/assignments/{assignment_id}/publish",
    response_model=schemas.Assignment,
    tags=["Assignments"],
)
def publish_assignment(
    assignment_id: str,
    db: Session = Depends(get_db),
):
    assignment = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assignment '{assignment_id}' not found.",
        )

    if not assignment.due_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assignment cannot be published without a valid due date.",
        )

    if not assignment.rubric:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assignment cannot be published without an associated rubric.",
        )

    if not assignment.rubric.criteria or len(assignment.rubric.criteria) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assignment rubric must contain at least one criterion.",
        )

    if assignment.rubric.total_points <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rubric total points must be greater than zero.",
        )

    assignment.is_published = True
    db.commit()
    db.refresh(assignment)
    return assignment


# ==========================================
# Submission Endpoints
# ==========================================

@app.post(
    "/api/submissions",
    response_model=schemas.Submission,
    status_code=status.HTTP_201_CREATED,
    tags=["Submissions"],
)
def create_submission(
    submission_in: schemas.SubmissionCreate,
    db: Session = Depends(get_db),
):
    # Rule 1: Verify assignment exists and is_published == True
    assignment = db.query(models.Assignment).filter(models.Assignment.id == submission_in.assignment_id).first()
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assignment '{submission_in.assignment_id}' not found.",
        )
    if not assignment.is_published:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot submit to an unpublished assignment.",
        )

    # Check learner exists
    learner = db.query(models.Learner).filter(models.Learner.id == submission_in.learner_id).first()
    if not learner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Learner '{submission_in.learner_id}' not found.",
        )

    # Rule 2: Verify learner is actively enrolled in assignment's course. Return 403 if unenrolled.
    enrollment = db.query(models.Enrollment).filter(
        models.Enrollment.course_id == assignment.course_id,
        models.Enrollment.learner_id == submission_in.learner_id,
    ).first()
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Learner is not enrolled in the course for this assignment.",
        )
    if not learner.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Learner account is inactive.",
        )

    # Rule 3: Count previous submissions for this learner/assignment. Check against assignment.max_attempts.
    previous_count = db.query(models.Submission).filter(
        models.Submission.assignment_id == assignment.id,
        models.Submission.learner_id == learner.id,
    ).count()

    if previous_count >= assignment.max_attempts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum submission attempts ({assignment.max_attempts}) exceeded.",
        )

    # Rule 4: Compare current UTC time against assignment.due_date. Set is_late.
    now_utc = submission_in.submitted_at or datetime.datetime.now(datetime.timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=datetime.timezone.utc)

    is_late = bool(now_utc > assignment.due_date)

    # Rule 5: Assign correct attempt_number
    attempt_number = previous_count + 1

    # ID assignment
    if submission_in.id:
        sub_id = submission_in.id
    else:
        total_subs = db.query(models.Submission).count() + 1
        sub_id = f"SUB-2026-{total_subs:06d}"
        while db.query(models.Submission).filter(models.Submission.id == sub_id).first():
            total_subs += 1
            sub_id = f"SUB-2026-{total_subs:06d}"

    db_submission = models.Submission(
        id=sub_id,
        assignment_id=assignment.id,
        learner_id=learner.id,
        attempt_number=attempt_number,
        submitted_at=now_utc,
        is_late=is_late,
        status="submitted",
    )
    db.add(db_submission)
    db.flush()

    # Add artifacts
    for art in submission_in.artifacts:
        db_artifact = models.SubmissionArtifact(
            submission_id=db_submission.id,
            file_name=art.file_name,
            file_type=art.file_type,
            file_size_bytes=art.file_size_bytes,
            storage_path=art.storage_path,
            uploaded_at=now_utc,
        )
        db.add(db_artifact)

    try:
        db.commit()
        db.refresh(db_submission)
        return db_submission
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Submission failed due to a database integrity conflict.",
        )


@app.get(
    "/api/submissions",
    response_model=List[schemas.Submission],
    tags=["Submissions"],
)
def list_submissions(
    assignment_id: Optional[str] = Query(None, description="Filter by assignment ID"),
    learner_id: Optional[str] = Query(None, description="Filter by learner ID"),
    skip: int = Query(0, ge=0, description="Records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max records to return"),
    db: Session = Depends(get_db),
):
    query = db.query(models.Submission)
    if assignment_id is not None:
        query = query.filter(models.Submission.assignment_id == assignment_id)
    if learner_id is not None:
        query = query.filter(models.Submission.learner_id == learner_id)
    return query.order_by(models.Submission.id).offset(skip).limit(limit).all()


@app.get(
    "/api/submissions/{submission_id}",
    response_model=schemas.Submission,
    tags=["Submissions"],
)
def get_submission(
    submission_id: str,
    db: Session = Depends(get_db),
):
    submission = db.query(models.Submission).filter(models.Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Submission '{submission_id}' not found.",
        )
    return submission



# ==========================================
# Grading Endpoints
# ==========================================

@app.post(
    "/api/submissions/{submission_id}/grade",
    response_model=schemas.Grade,
    status_code=status.HTTP_201_CREATED,
    tags=["Grading"],
)
def grade_submission(
    submission_id: str,
    grade_in: schemas.GradeCreate,
    db: Session = Depends(get_db),
):
    submission = db.query(models.Submission).filter(models.Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Submission '{submission_id}' not found.",
        )

    if submission.grade:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Submission '{submission_id}' has already been graded.",
        )

    rubric = submission.assignment.rubric
    if not rubric:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assignment has no associated rubric to evaluate against.",
        )

    criteria_map = {c.id: c for c in rubric.criteria}

    # 1. Validate criterion scores against rubric criteria max_marks
    for cs in grade_in.criterion_scores:
        if cs.criterion_id not in criteria_map:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Criterion ID {cs.criterion_id} does not belong to rubric for assignment '{submission.assignment_id}'.",
            )
        criterion = criteria_map[cs.criterion_id]
        if cs.score > criterion.max_marks:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Score {cs.score} for criterion '{criterion.name}' exceeds maximum marks ({criterion.max_marks}).",
            )
        if cs.score < 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Score for criterion '{criterion.name}' cannot be negative.",
            )

    # 2. Calculate raw_score as sum of criterion scores
    raw_score = round(sum(cs.score for cs in grade_in.criterion_scores), 2)

    # 3. Late penalty calculation (applied ONCE if is_late is True)
    if submission.is_late:
        late_penalty = 10.0 if grade_in.late_penalty is None else grade_in.late_penalty
    else:
        late_penalty = 0.0

    # 4. Calculate final_score = raw_score - late_penalty, not below 0
    final_score = max(0.0, round(raw_score - late_penalty, 2))
    is_passing = bool(final_score >= 60.0)

    # Generate Grade ID
    grade_count = db.query(models.Grade).count() + 1
    grade_id = f"GRD-2026-{grade_count:06d}"
    while db.query(models.Grade).filter(models.Grade.id == grade_id).first():
        grade_count += 1
        grade_id = f"GRD-2026-{grade_count:06d}"

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    db_grade = models.Grade(
        id=grade_id,
        submission_id=submission.id,
        raw_score=raw_score,
        late_penalty=late_penalty,
        final_score=final_score,
        is_passing=is_passing,
        graded_at=now_utc,
    )
    db.add(db_grade)
    db.flush()

    for cs in grade_in.criterion_scores:
        db_cs = models.CriterionScore(
            grade_id=db_grade.id,
            criterion_id=cs.criterion_id,
            score=cs.score,
        )
        db.add(db_cs)

    if grade_in.feedback:
        fb_count = db.query(models.Feedback).count() + 1
        fb_id = f"FDB-2026-{fb_count:06d}"
        while db.query(models.Feedback).filter(models.Feedback.id == fb_id).first():
            fb_count += 1
            fb_id = f"FDB-2026-{fb_count:06d}"

        db_fb = models.Feedback(
            id=fb_id,
            submission_id=submission.id,
            comments=grade_in.feedback.comments,
            strengths=grade_in.feedback.strengths,
            improvements=grade_in.feedback.improvements,
            created_at=now_utc,
        )
        db.add(db_fb)

    submission.status = "graded"

    try:
        db.commit()
        db.refresh(db_grade)
        return db_grade
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Grading transaction failed due to an integrity conflict.",
        )


@app.get(
    "/api/submissions/{submission_id}/grade",
    response_model=schemas.Grade,
    tags=["Grading"],
)
def get_submission_grade(
    submission_id: str,
    db: Session = Depends(get_db),
):
    submission = db.query(models.Submission).filter(models.Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Submission '{submission_id}' not found.",
        )

    if not submission.grade:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Submission '{submission_id}' has not been graded yet.",
        )

    return submission.grade


# ==========================================
# Resubmission Endpoints
# ==========================================

@app.post(
    "/api/submissions/{submission_id}/resubmit",
    response_model=schemas.Resubmission,
    status_code=status.HTTP_201_CREATED,
    tags=["Resubmissions"],
)
def request_resubmission(
    submission_id: str,
    resub_in: schemas.ResubmissionCreate,
    db: Session = Depends(get_db),
):
    submission = db.query(models.Submission).filter(models.Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Submission '{submission_id}' not found.",
        )

    # Policy Check: Assignment allow_resubmission
    if not submission.assignment.allow_resubmission:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resubmission is not permitted for this assignment.",
        )

    # Max attempts check
    attempts = db.query(models.Submission).filter(
        models.Submission.assignment_id == submission.assignment_id,
        models.Submission.learner_id == submission.learner_id,
    ).count()

    if attempts >= submission.assignment.max_attempts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum submission attempts reached.",
        )

    # Create new attempt submission or link
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    if resub_in.new_submission_id:
        new_sub_id = resub_in.new_submission_id
    else:
        total_subs = db.query(models.Submission).count() + 1
        new_sub_id = f"SUB-2026-{total_subs:06d}"
        while db.query(models.Submission).filter(models.Submission.id == new_sub_id).first():
            total_subs += 1
            new_sub_id = f"SUB-2026-{total_subs:06d}"

        new_sub = models.Submission(
            id=new_sub_id,
            assignment_id=submission.assignment_id,
            learner_id=submission.learner_id,
            attempt_number=attempts + 1,
            submitted_at=now_utc,
            is_late=bool(now_utc > submission.assignment.due_date),
            status="resubmitted",
        )
        db.add(new_sub)
        db.flush()

    resub_count = db.query(models.Resubmission).count() + 1
    resub_id = f"RSB-2026-{resub_count:06d}"
    while db.query(models.Resubmission).filter(models.Resubmission.id == resub_id).first():
        resub_count += 1
        resub_id = f"RSB-2026-{resub_count:06d}"

    db_resub = models.Resubmission(
        id=resub_id,
        original_submission_id=submission.id,
        new_submission_id=new_sub_id,
        reason=resub_in.reason,
        requested_at=now_utc,
    )
    db.add(db_resub)

    try:
        db.commit()
        db.refresh(db_resub)
        return db_resub
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Resubmission failed due to a database integrity conflict.",
        )


# ==========================================
# Appeal & Audit Endpoints
# ==========================================

@app.post(
    "/api/grades/{grade_id}/appeal",
    response_model=schemas.Appeal,
    status_code=status.HTTP_201_CREATED,
    tags=["Appeals"],
)
def file_appeal(
    grade_id: str,
    appeal_in: schemas.AppealCreate,
    db: Session = Depends(get_db),
):
    grade = db.query(models.Grade).filter(models.Grade.id == grade_id).first()
    if not grade:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Grade '{grade_id}' not found.",
        )

    submission = grade.submission
    # Check for duplicate pending appeal on this submission
    existing = db.query(models.Appeal).filter(
        models.Appeal.submission_id == submission.id,
        models.Appeal.status == "pending",
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A pending appeal already exists for this submission.",
        )

    appeal_count = db.query(models.Appeal).count() + 1
    appeal_id = f"APL-2026-{appeal_count:06d}"
    while db.query(models.Appeal).filter(models.Appeal.id == appeal_id).first():
        appeal_count += 1
        appeal_id = f"APL-2026-{appeal_count:06d}"

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    db_appeal = models.Appeal(
        id=appeal_id,
        submission_id=submission.id,
        learner_id=submission.learner_id,
        reason=appeal_in.reason,
        status="pending",
        original_score=grade.final_score,
        updated_score=None,
        created_at=now_utc,
        resolved_at=None,
    )
    db.add(db_appeal)

    try:
        db.commit()
        db.refresh(db_appeal)
        return db_appeal
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Appeal creation failed due to an integrity conflict.",
        )


@app.patch(
    "/api/appeals/{appeal_id}",
    response_model=schemas.Appeal,
    tags=["Appeals"],
)
def decide_appeal(
    appeal_id: str,
    decision_in: schemas.AppealUpdate,
    db: Session = Depends(get_db),
):
    appeal = db.query(models.Appeal).filter(models.Appeal.id == appeal_id).first()
    if not appeal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appeal '{appeal_id}' not found.",
        )

    if appeal.status in ("approved", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Appeal '{appeal_id}' has already been resolved ({appeal.status}).",
        )

    now_utc = datetime.datetime.now(datetime.timezone.utc)

    if decision_in.status == "approved":
        if decision_in.updated_score is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="updated_score is required when approving an appeal.",
            )

        rubric = appeal.submission.assignment.rubric
        rubric_max = float(rubric.total_points) if rubric else 100.0

        if decision_in.updated_score < 0 or decision_in.updated_score > rubric_max:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"updated_score must be between 0 and {rubric_max}.",
            )

        grade = appeal.submission.grade
        if not grade:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No grade record found for this submission.",
            )

        old_score = grade.final_score
        new_score = decision_in.updated_score

        # Update grade
        grade.final_score = new_score
        grade.is_passing = bool(new_score >= 60.0)

        # CRITICAL AUDIT RULE: Generate immutable GradeAudit record
        audit_record = models.GradeAudit(
            grade_id=grade.id,
            previous_score=old_score,
            new_score=new_score,
            change_reason=decision_in.reason or f"Appeal {appeal.id} approved: score updated from {old_score} to {new_score}",
            changed_at=now_utc,
        )
        db.add(audit_record)

        appeal.status = "approved"
        appeal.updated_score = new_score
        appeal.resolved_at = now_utc

    elif decision_in.status == "rejected":
        appeal.status = "rejected"
        appeal.updated_score = appeal.original_score
        appeal.resolved_at = now_utc

    try:
        db.commit()
        db.refresh(appeal)
        return appeal
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Failed to record appeal decision.",
        )


@app.get(
    "/api/grades/{grade_id}/audit",
    response_model=List[schemas.GradeAudit],
    tags=["Grading"],
)
def get_grade_audit_history(
    grade_id: str,
    db: Session = Depends(get_db),
):
    grade = db.query(models.Grade).filter(models.Grade.id == grade_id).first()
    if not grade:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Grade '{grade_id}' not found.",
        )

    audits = (
        db.query(models.GradeAudit)
        .filter(models.GradeAudit.grade_id == grade_id)
        .order_by(models.GradeAudit.id.asc())
        .all()
    )
    return audits



# ==========================================
# Dashboard & Analytics Endpoints
# ==========================================

@app.get(
    "/api/dashboard/metrics",
    tags=["Dashboard"],
)
def get_dashboard_metrics(db: Session = Depends(get_db)):
    total_courses = db.query(models.Course).count()
    total_learners = db.query(models.Learner).count()
    total_assignments = db.query(models.Assignment).count()
    total_submissions = db.query(models.Submission).count()

    avg_score = db.query(func.avg(models.Grade.final_score)).scalar()
    average_score = round(float(avg_score), 2) if avg_score is not None else 0.0

    return {
        "total_courses": total_courses,
        "total_learners": total_learners,
        "total_assignments": total_assignments,
        "total_submissions": total_submissions,
        "average_score": average_score,
    }


@app.get(
    "/api/dashboard/anomalies",
    tags=["Dashboard"],
)
def get_dashboard_anomalies(db: Session = Depends(get_db)):
    anomalies = []

    # 1. Submissions by learners not enrolled in the assignment's course
    unenrolled_query = (
        db.query(models.Submission)
        .join(models.Assignment, models.Submission.assignment_id == models.Assignment.id)
        .outerjoin(
            models.Enrollment,
            (models.Enrollment.course_id == models.Assignment.course_id)
            & (models.Enrollment.learner_id == models.Submission.learner_id),
        )
        .filter(models.Enrollment.id.is_(None))
        .all()
    )
    for sub in unenrolled_query:
        anomalies.append({
            "type": "Unenrolled Learner",
            "severity": "HIGH",
            "entity_id": sub.id,
            "details": f"Submission {sub.id} by learner {sub.learner_id} lacks valid enrollment in course {sub.assignment.course_id} (Assignment {sub.assignment_id}).",
        })

    # 2. Grades where raw_score exceeds the assignment rubric's total_points
    exceeded_query = (
        db.query(models.Grade, models.Rubric.total_points)
        .join(models.Submission, models.Grade.submission_id == models.Submission.id)
        .join(models.Assignment, models.Submission.assignment_id == models.Assignment.id)
        .join(models.Rubric, models.Assignment.id == models.Rubric.assignment_id)
        .filter(
            (models.Grade.raw_score > models.Rubric.total_points)
            | (models.Grade.final_score > models.Rubric.total_points)
        )
        .all()
    )
    for grade, rubric_points in exceeded_query:
        anomalies.append({
            "type": "Score Exceeds Rubric Maximum",
            "severity": "HIGH",
            "entity_id": grade.id,
            "details": f"Grade {grade.id} on submission {grade.submission_id} has score {grade.final_score} exceeding rubric total points ({rubric_points}).",
        })

    # 3. Grades where the applied penalty deduction exceeds the standard policy (late penalty applied twice)
    double_penalty_query = (
        db.query(models.Grade)
        .join(models.Submission, models.Grade.submission_id == models.Submission.id)
        .filter(
            models.Submission.is_late.is_(True),
            (models.Grade.late_penalty >= 20.0)
            | (func.round(models.Grade.raw_score - models.Grade.final_score, 2) >= 20.0),
        )
        .all()
    )
    for grade in double_penalty_query:
        anomalies.append({
            "type": "Duplicate Late Penalty",
            "severity": "MEDIUM",
            "entity_id": grade.id,
            "details": f"Grade {grade.id} on late submission {grade.submission_id} received duplicate penalty deduction ({grade.late_penalty} pts deducted instead of standard 10.0).",
        })

    # 4. Approved appeals that have no corresponding record in the grade_audits table
    approved_appeals = (
        db.query(models.Appeal)
        .filter(
            models.Appeal.status == "approved",
            models.Appeal.original_score != models.Appeal.updated_score,
        )
        .all()
    )
    for apl in approved_appeals:
        grade = apl.submission.grade if (apl.submission and apl.submission.grade) else None
        if grade:
            audit_exists = (
                db.query(models.GradeAudit)
                .filter(models.GradeAudit.grade_id == grade.id)
                .first()
            )
            if not audit_exists:
                anomalies.append({
                    "type": "Missing Appeal Audit History",
                    "severity": "CRITICAL",
                    "entity_id": apl.id,
                    "details": f"Appeal {apl.id} revised grade {grade.id} score from {apl.original_score} to {apl.updated_score} without an audit history record in grade_audits.",
                })

    return anomalies
