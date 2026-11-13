from datetime import datetime
import re
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

# Regex patterns for validation
COURSE_ID_PATTERN = re.compile(r"^CRS-\d{4}-\d{6}$")
LEARNER_ID_PATTERN = re.compile(r"^LRN-\d{4}-\d{6}$")
ASSIGNMENT_ID_PATTERN = re.compile(r"^ASN-\d{4}-\d{6}$")
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


# ==========================================
# Course Schemas
# ==========================================

class CourseCreate(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    is_active: bool = True

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not v or not COURSE_ID_PATTERN.match(v.strip()):
            raise ValueError("Course ID must follow the format 'CRS-YYYY-NNNNNN' (e.g., 'CRS-2026-000001').")
        return v.strip()

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if v is None or not v.strip():
            raise ValueError("Course name cannot be empty or whitespace.")
        return v.strip()


class CourseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            raise ValueError("Course name cannot be explicitly set to null.")
        if not v.strip():
            raise ValueError("Course name cannot be empty or whitespace.")
        return v.strip()

    @field_validator("is_active")
    @classmethod
    def validate_is_active(cls, v: Optional[bool]) -> Optional[bool]:
        if v is None:
            raise ValueError("is_active cannot be explicitly set to null.")
        return v


class CourseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime


# ==========================================
# Learner Schemas
# ==========================================

class LearnerCreate(BaseModel):
    id: str
    name: str
    email: str
    is_active: bool = True

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not v or not LEARNER_ID_PATTERN.match(v.strip()):
            raise ValueError("Learner ID must follow the format 'LRN-YYYY-NNNNNN' (e.g., 'LRN-2026-000001').")
        return v.strip()

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if v is None or not v.strip():
            raise ValueError("Learner name cannot be empty or whitespace.")
        return v.strip()

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if v is None:
            raise ValueError("Email cannot be empty.")
        v_clean = v.strip().lower()
        if not EMAIL_PATTERN.match(v_clean):
            raise ValueError(f"Invalid email address: '{v}'.")
        return v_clean


class LearnerUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            raise ValueError("Learner name cannot be explicitly set to null.")
        if not v.strip():
            raise ValueError("Learner name cannot be empty or whitespace.")
        return v.strip()

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            raise ValueError("Email cannot be explicitly set to null.")
        v_clean = v.strip().lower()
        if not EMAIL_PATTERN.match(v_clean):
            raise ValueError(f"Invalid email address: '{v}'.")
        return v_clean

    @field_validator("is_active")
    @classmethod
    def validate_is_active(cls, v: Optional[bool]) -> Optional[bool]:
        if v is None:
            raise ValueError("is_active cannot be explicitly set to null.")
        return v


class LearnerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: str
    is_active: bool
    created_at: datetime


# ==========================================
# Enrollment Schemas
# ==========================================

class EnrollmentCreate(BaseModel):
    course_id: str
    learner_id: str
    enrollment_date: Optional[datetime] = None

    @field_validator("course_id")
    @classmethod
    def validate_course_id(cls, v: str) -> str:
        if not v or not COURSE_ID_PATTERN.match(v.strip()):
            raise ValueError("Course ID must follow format 'CRS-YYYY-NNNNNN'.")
        return v.strip()

    @field_validator("learner_id")
    @classmethod
    def validate_learner_id(cls, v: str) -> str:
        if not v or not LEARNER_ID_PATTERN.match(v.strip()):
            raise ValueError("Learner ID must follow format 'LRN-YYYY-NNNNNN'.")
        return v.strip()

    @field_validator("enrollment_date")
    @classmethod
    def validate_enrollment_date(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is not None:
            if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
                raise ValueError("Enrollment date must be timezone-aware.")
        return v


class EnrollmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: str
    learner_id: str
    enrollment_date: datetime


# ==========================================
# Rubric & Criterion Schemas
# ==========================================

class RubricCriterionCreate(BaseModel):
    name: str
    max_marks: int

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Criterion name cannot be empty or whitespace.")
        return v.strip()

    @field_validator("max_marks")
    @classmethod
    def validate_max_marks(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("max_marks must be greater than zero.")
        return v


class RubricCriterion(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rubric_id: str
    name: str
    max_marks: int


class RubricCreate(BaseModel):
    id: Optional[str] = None
    total_points: int = 100
    criteria: List[RubricCriterionCreate] = []

    @field_validator("total_points")
    @classmethod
    def validate_total_points(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("total_points must be greater than zero.")
        return v


class Rubric(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    assignment_id: str
    total_points: int
    criteria: List[RubricCriterion] = []


# ==========================================
# Assignment Schemas
# ==========================================

class AssignmentCreate(BaseModel):
    id: Optional[str] = None
    course_id: str
    title: str
    due_date: datetime
    max_attempts: int = 1
    allow_resubmission: bool = False
    rubric: Optional[RubricCreate] = None

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not ASSIGNMENT_ID_PATTERN.match(v.strip()):
                raise ValueError("Assignment ID must follow format 'ASN-YYYY-NNNNNN'.")
            return v.strip()
        return None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Assignment title cannot be empty or whitespace.")
        return v.strip()

    @field_validator("due_date")
    @classmethod
    def validate_due_date(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            raise ValueError("due_date must be timezone-aware.")
        return v

    @field_validator("max_attempts")
    @classmethod
    def validate_max_attempts(cls, v: int) -> int:
        if v < 1:
            raise ValueError("max_attempts must be at least 1.")
        return v

    @model_validator(mode="after")
    def validate_resubmission_attempts(self):
        if not self.allow_resubmission and self.max_attempts > 1:
            raise ValueError("If resubmission is disabled, max_attempts must be 1.")
        return self


class AssignmentUpdate(BaseModel):
    title: Optional[str] = None
    due_date: Optional[datetime] = None
    max_attempts: Optional[int] = None
    allow_resubmission: Optional[bool] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            raise ValueError("Assignment title cannot be explicitly set to null.")
        if not v.strip():
            raise ValueError("Assignment title cannot be empty or whitespace.")
        return v.strip()

    @field_validator("due_date")
    @classmethod
    def validate_due_date(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is not None:
            if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
                raise ValueError("due_date must be timezone-aware.")
        return v


class Assignment(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    course_id: str
    title: str
    due_date: datetime
    max_attempts: int
    allow_resubmission: bool
    is_published: bool
    rubric: Optional[Rubric] = None


# ==========================================
# Submission Artifact Schemas
# ==========================================

class SubmissionArtifactCreate(BaseModel):
    file_name: str
    file_type: str = "pdf"
    file_size_bytes: int = 1024
    storage_path: str = "/artifacts/default"

    @field_validator("file_name")
    @classmethod
    def validate_file_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("file_name cannot be empty or whitespace.")
        return v.strip()


class SubmissionArtifact(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    submission_id: str
    file_name: str
    file_type: str
    file_size_bytes: int
    storage_path: str
    uploaded_at: datetime


# ==========================================
# Submission Schemas
# ==========================================

class SubmissionCreate(BaseModel):
    id: Optional[str] = None
    assignment_id: str
    learner_id: str
    artifacts: List[SubmissionArtifactCreate] = []
    submitted_at: Optional[datetime] = None

    @field_validator("submitted_at")
    @classmethod
    def validate_submitted_at(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is not None:
            if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
                raise ValueError("submitted_at must be timezone-aware.")
        return v


class Submission(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    assignment_id: str
    learner_id: str
    attempt_number: int
    submitted_at: datetime
    is_late: bool
    status: str
    artifacts: List[SubmissionArtifact] = []



# ==========================================
# Evaluation Schemas (CriterionScore, Feedback, Grade)
# ==========================================

class CriterionScoreCreate(BaseModel):
    criterion_id: int
    score: float

    @field_validator("score")
    @classmethod
    def validate_score(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Criterion score cannot be negative.")
        return round(v, 2)


class CriterionScore(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    grade_id: str
    criterion_id: int
    score: float


class FeedbackCreate(BaseModel):
    comments: str
    strengths: Optional[str] = None
    improvements: Optional[str] = None

    @field_validator("comments")
    @classmethod
    def validate_comments(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Feedback comments cannot be empty or whitespace.")
        return v.strip()


class Feedback(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    submission_id: str
    comments: str
    strengths: Optional[str] = None
    improvements: Optional[str] = None
    created_at: datetime


class GradeCreate(BaseModel):
    criterion_scores: List[CriterionScoreCreate]
    feedback: Optional[FeedbackCreate] = None
    late_penalty: Optional[float] = None

    @field_validator("criterion_scores")
    @classmethod
    def validate_criterion_scores(cls, v: List[CriterionScoreCreate]) -> List[CriterionScoreCreate]:
        if not v:
            raise ValueError("At least one criterion score must be provided.")
        return v


class GradeUpdate(BaseModel):
    raw_score: Optional[float] = None
    late_penalty: Optional[float] = None
    final_score: Optional[float] = None
    is_passing: Optional[bool] = None


class Grade(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    submission_id: str
    raw_score: float
    late_penalty: float
    final_score: float
    is_passing: bool
    graded_at: datetime
    criterion_scores: List[CriterionScore] = []
    feedback: Optional[Feedback] = None


# ==========================================
# Resubmission Schemas
# ==========================================

class ResubmissionCreate(BaseModel):
    reason: str
    new_submission_id: Optional[str] = None

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Resubmission reason cannot be empty or whitespace.")
        return v.strip()


class ResubmissionUpdate(BaseModel):
    reason: Optional[str] = None


class Resubmission(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    original_submission_id: str
    new_submission_id: Optional[str] = None
    reason: str
    requested_at: datetime


# ==========================================
# Appeal & Audit Schemas
# ==========================================

class AppealCreate(BaseModel):
    reason: str

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Appeal reason cannot be empty or whitespace.")
        return v.strip()


class AppealUpdate(BaseModel):
    status: str  # approved, rejected
    updated_score: Optional[float] = None
    reason: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        v_clean = v.strip().lower()
        if v_clean not in ("approved", "rejected"):
            raise ValueError("Appeal status must be 'approved' or 'rejected'.")
        return v_clean


class Appeal(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    submission_id: str
    learner_id: str
    reason: str
    status: str
    original_score: float
    updated_score: Optional[float] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None


class GradeAudit(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    grade_id: str
    previous_score: float
    new_score: float
    change_reason: str
    changed_at: datetime
