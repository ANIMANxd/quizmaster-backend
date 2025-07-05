from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "user"
class UserLogin(BaseModel):
    email: EmailStr
    password: str
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
class LoginResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str   
    token: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    # is_active: bool

    class Config:
        orm_mode = True

class UserStatusUpdate(BaseModel):
    is_active: bool


#SUbject Schema
class SubjectBase(BaseModel):
    name: str
    description: str | None = None
class SubjectCreate(SubjectBase):
    pass
class SubjectUpdate(SubjectBase):
    pass
class SubjectOut(SubjectBase):
    id: int
    name: str
    description: str 
    class Config:
        orm_mode = True 

#dashboard stats schema
class DashboardStats(BaseModel):
    subjects: int
    chapters: int = 0  # Default to 0 if you don’t have this table yet
    quizzes: int = 0
    questions: int = 0

class AdminDashboardStats(BaseModel):
    subjects: int
    chapters: int
    quizzes: int
    questions: int
    users: int

class RecentActivity(BaseModel):
    user_name: str
    quiz_title: str
    score: int
    timestamp: datetime

class QuizStat(BaseModel):
    quiz_id: int
    quiz_title: str
    value: int # Can be attempt_count or average_score

class AdminDashboardData(BaseModel):
    stats: AdminDashboardStats
    recent_activity: List[RecentActivity]
    most_attempted_quizzes: List[QuizStat]
    lowest_scoring_quizzes: List[QuizStat]


class ChapterCreate(BaseModel):
    name: str
    subject_id: int

class ChapterRead(ChapterCreate):
    id: int

    class Config:
        orm_mode = True


class OptionCreate(BaseModel):
    option_text: str
    is_correct: bool

class OptionRead(OptionCreate):
    id: int
    class Config:
        orm_mode = True

class QuestionCreate(BaseModel):
    question_text: str
    quiz_id: int
    marks: int
    question_type: str
    options: List[OptionCreate]

class QuestionRead(BaseModel):
    id: int
    question_text: str
    quiz_id: int 
    marks: int
    question_type: str
    options: List[OptionRead]
    class Config:
        orm_mode = True

class QuizCreate(BaseModel):
    title: str
    chapter_id: int

class QuizUpdate(BaseModel):
    title: str
    chapter_id: int



class QuizAttemptCreate(BaseModel):
    user_id: int
    quiz_id: int
    score: int


# schemas.py

class QuizRead(BaseModel):
    id: int
    title: str
    chapter_id: Optional[int] = None # <-- ADD THIS LINE
    is_ai_generated: bool
    created_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class QuizAttemptRead(BaseModel):
    id: int
    user_id: int
    quiz_id: int
    score: int
    attempt_number: int
    timestamp: datetime
    quiz: QuizRead  # <-- This is crucial for the history page

    class Config:
        orm_mode = True


class PerformanceBySubject(BaseModel):
    subject_name: str
    average_score: float
    attempts_count: int

class RecentAttempt(BaseModel):
    quiz_title: str
    score: int
    timestamp: datetime

class QuizPerformance(BaseModel):
    quiz_id: int
    quiz_title: str
    best_score: int

class UserPerformance(BaseModel):
    total_quizzes_taken: int
    total_attempts: int
    average_score: float
    best_subject: Optional[str] = None
    worst_subject: Optional[str] = None
    performance_by_subject: List[PerformanceBySubject]
    recent_attempts: List[RecentAttempt]
    best_performing_quizzes: List[QuizPerformance]
    improvement_areas: List[QuizPerformance]


class SubjectAssignment(BaseModel):
    user_id: int
    subject_ids: List[int]