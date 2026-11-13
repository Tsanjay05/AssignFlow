import datetime
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base, UTCDateTime


def utc_now():
    """Helper to return current UTC timezone-aware datetime."""
    return datetime.datetime.now(datetime.timezone.utc)


class Course(Base):
    __tablename__ = "courses"

    id = Column(String, primary_key=True, index=True)  # Format: CRS-YYYY-NNNNNN
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(UTCDateTime, default=utc_now, nullable=False)

    # Relationships
    enrollments = relationship(
        "Enrollment",
        back_populates="course",
        passive_deletes=True,
    )
    assignments = relationship(
        "Assignment",
        back_populates="course",
        passive_deletes=True,
    )


class Learner(Base):
    __tablename__ = "learners"

    id = Column(String, primary_key=True, index=True)  # Format: LRN-YYYY-NNNNNN
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(UTCDateTime, default=utc_now, nullable=False)

    # Relationships
    enrollments = relationship(
        "Enrollment",
        back_populates="learner",
        passive_deletes=True,
    )
    submissions = relationship(
        "Submission",
        back_populates="learner",
        passive_deletes=True,
    )
    appeals = relationship(
        "Appeal",
        back_populates="learner",
        passive_deletes=True,
    )


class Enrollment(Base):
    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(String, ForeignKey("courses.id"), nullable=False, index=True)
    learner_id = Column(String, ForeignKey("learners.id"), nullable=False, index=True)
    enrollment_date = Column(UTCDateTime, default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("course_id", "learner_id", name="uq_enrollment_course_learner"),
        Index("ix_enrollments_course_learner", "course_id", "learner_id"),
    )

    # Relationships
    course = relationship("Course", back_populates="enrollments")
    learner = relationship("Learner", back_populates="enrollments")


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(String, primary_key=True, index=True)  # Format: ASN-YYYY-NNNNNN
    course_id = Column(String, ForeignKey("courses.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    due_date = Column(UTCDateTime, nullable=False)
    max_attempts = Column(Integer, default=1, nullable=False)
    allow_resubmission = Column(Boolean, default=False, nullable=False)
    is_published = Column(Boolean, default=False, nullable=False)

    __table_args__ = (
        CheckConstraint("max_attempts >= 1", name="ck_assignment_max_attempts_min"),
        CheckConstraint(
            "(allow_resubmission = 1) OR (max_attempts = 1)",
            name="ck_assignment_resubmission_attempts",
        ),
    )

    # Relationships
    course = relationship("Course", back_populates="assignments")
    rubric = relationship("Rubric", back_populates="assignment", uselist=False)
    submissions = relationship(
        "Submission",
        back_populates="assignment",
        passive_deletes=True,
    )


class Rubric(Base):
    __tablename__ = "rubrics"

    id = Column(String, primary_key=True)
    assignment_id = Column(
        String,
        ForeignKey("assignments.id"),
        unique=True,
        nullable=False,
        index=True,
    )
    total_points = Column(Integer, default=100, nullable=False)

    __table_args__ = (
        CheckConstraint("total_points > 0", name="ck_rubric_total_points_gt_zero"),
        UniqueConstraint("assignment_id", name="uq_rubric_assignment_id"),
    )

    # Relationships
    assignment = relationship("Assignment", back_populates="rubric")
    criteria = relationship("RubricCriterion", back_populates="rubric")


class RubricCriterion(Base):
    __tablename__ = "rubric_criteria"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rubric_id = Column(String, ForeignKey("rubrics.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    max_marks = Column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint("max_marks > 0", name="ck_rubric_criterion_max_marks_gt_zero"),
    )

    # Relationships
    rubric = relationship("Rubric", back_populates="criteria")
    criterion_scores = relationship("CriterionScore", back_populates="criterion")


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(String, primary_key=True, index=True)  # Format: SUB-YYYY-NNNNNN
    assignment_id = Column(String, ForeignKey("assignments.id"), nullable=False, index=True)
    learner_id = Column(String, ForeignKey("learners.id"), nullable=False, index=True)
    attempt_number = Column(Integer, default=1, nullable=False)
    submitted_at = Column(UTCDateTime, default=utc_now, nullable=False)
    is_late = Column(Boolean, default=False, nullable=False)
    status = Column(String, default="submitted", nullable=False)  # submitted, graded, resubmitted

    # Relationships
    assignment = relationship("Assignment", back_populates="submissions")
    learner = relationship("Learner", back_populates="submissions")
    artifacts = relationship("SubmissionArtifact", back_populates="submission", cascade="all, delete-orphan")
    grade = relationship("Grade", back_populates="submission", uselist=False)
    feedback = relationship("Feedback", back_populates="submission", uselist=False)
    appeals = relationship("Appeal", back_populates="submission")


class SubmissionArtifact(Base):
    __tablename__ = "submission_artifacts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    submission_id = Column(String, ForeignKey("submissions.id"), nullable=False, index=True)
    file_name = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    storage_path = Column(String, nullable=False)
    uploaded_at = Column(UTCDateTime, default=utc_now, nullable=False)

    # Relationships
    submission = relationship("Submission", back_populates="artifacts")


class Grade(Base):
    __tablename__ = "grades"

    id = Column(String, primary_key=True, index=True)  # Format: GRD-YYYY-NNNNNN
    submission_id = Column(String, ForeignKey("submissions.id"), unique=True, nullable=False, index=True)
    raw_score = Column(Float, nullable=False)
    late_penalty = Column(Float, default=0.0, nullable=False)
    final_score = Column(Float, nullable=False)
    is_passing = Column(Boolean, default=True, nullable=False)
    graded_at = Column(UTCDateTime, default=utc_now, nullable=False)

    # Relationships
    submission = relationship("Submission", back_populates="grade")
    criterion_scores = relationship("CriterionScore", back_populates="grade", cascade="all, delete-orphan")
    audits = relationship("GradeAudit", back_populates="grade")

    @property
    def feedback(self):
        return self.submission.feedback if self.submission else None


class CriterionScore(Base):
    __tablename__ = "criterion_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    grade_id = Column(String, ForeignKey("grades.id"), nullable=False, index=True)
    criterion_id = Column(Integer, ForeignKey("rubric_criteria.id"), nullable=False, index=True)
    score = Column(Float, nullable=False)

    # Relationships
    grade = relationship("Grade", back_populates="criterion_scores")
    criterion = relationship("RubricCriterion", back_populates="criterion_scores")


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(String, primary_key=True, index=True)  # Format: FDB-YYYY-NNNNNN
    submission_id = Column(String, ForeignKey("submissions.id"), unique=True, nullable=False, index=True)
    comments = Column(String, nullable=False)
    strengths = Column(String, nullable=True)
    improvements = Column(String, nullable=True)
    created_at = Column(UTCDateTime, default=utc_now, nullable=False)

    # Relationships
    submission = relationship("Submission", back_populates="feedback")


class Resubmission(Base):
    __tablename__ = "resubmissions"

    id = Column(String, primary_key=True, index=True)  # Format: RSB-YYYY-NNNNNN
    original_submission_id = Column(String, ForeignKey("submissions.id"), nullable=False, index=True)
    new_submission_id = Column(String, ForeignKey("submissions.id"), nullable=True, index=True)
    reason = Column(String, nullable=False)
    requested_at = Column(UTCDateTime, default=utc_now, nullable=False)

    # Relationships
    original_submission = relationship("Submission", foreign_keys=[original_submission_id])
    new_submission = relationship("Submission", foreign_keys=[new_submission_id])


class Appeal(Base):
    __tablename__ = "appeals"

    id = Column(String, primary_key=True, index=True)  # Format: APL-YYYY-NNNNNN
    submission_id = Column(String, ForeignKey("submissions.id"), nullable=False, index=True)
    learner_id = Column(String, ForeignKey("learners.id"), nullable=False, index=True)
    reason = Column(String, nullable=False)
    status = Column(String, default="pending", nullable=False)  # pending, approved, rejected
    original_score = Column(Float, nullable=False)
    updated_score = Column(Float, nullable=True)
    created_at = Column(UTCDateTime, default=utc_now, nullable=False)
    resolved_at = Column(UTCDateTime, nullable=True)

    # Relationships
    submission = relationship("Submission", back_populates="appeals")
    learner = relationship("Learner", back_populates="appeals")


class GradeAudit(Base):
    __tablename__ = "grade_audits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    grade_id = Column(String, ForeignKey("grades.id"), nullable=False, index=True)
    previous_score = Column(Float, nullable=False)
    new_score = Column(Float, nullable=False)
    change_reason = Column(String, nullable=False)
    changed_at = Column(UTCDateTime, default=utc_now, nullable=False)

    # Relationships
    grade = relationship("Grade", back_populates="audits")
