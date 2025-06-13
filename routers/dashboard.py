from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import Subject 
from schemas import DashboardStats
from models import Chapter, Quiz, Question, User
from sqlalchemy import func
from fastapi import Security
import models
import schemas
from .dependencies import require_admin

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)

@router.get("/dashboard-data", response_model=schemas.AdminDashboardData)
def get_admin_dashboard_data(
    admin: models.User = Security(require_admin),
    db: Session = Depends(get_db)
):
    """
    Gathers all necessary data for the main admin dashboard.
    """
    # 1. Basic Stats
    stats = schemas.AdminDashboardStats(
        subjects=db.query(models.Subject).count(),
        chapters=db.query(models.Chapter).count(),
        quizzes=db.query(models.Quiz).count(),
        questions=db.query(models.Question).count(),
        users=db.query(models.User).filter(models.User.role == 'user').count()
    )

    # 2. Recent Activity Feed (last 5 attempts)
    recent_attempts_query = db.query(models.QuizAttempt).order_by(
        models.QuizAttempt.timestamp.desc()
    ).limit(5).all()
    recent_activity = [
        schemas.RecentActivity(
            user_name=attempt.user.name,
            quiz_title=attempt.quiz.title,
            score=attempt.score,
            timestamp=attempt.timestamp
        ) for attempt in recent_attempts_query
    ]

    # 3. Most Attempted Quizzes
    most_attempted_query = db.query(
        models.Quiz.id,
        models.Quiz.title,
        func.count(models.QuizAttempt.id).label('attempt_count')
    ).join(models.QuizAttempt, models.Quiz.id == models.QuizAttempt.quiz_id)\
     .group_by(models.Quiz.id, models.Quiz.title)\
     .order_by(func.count(models.QuizAttempt.id).desc())\
     .limit(5).all()
    most_attempted_quizzes = [
        schemas.QuizStat(quiz_id=qid, quiz_title=title, value=count)
        for qid, title, count in most_attempted_query
    ]

    # 4. Lowest Scoring Quizzes (by average score)
    lowest_scoring_query = db.query(
        models.Quiz.id,
        models.Quiz.title,
        func.avg(models.QuizAttempt.score).label('avg_score')
    ).join(models.QuizAttempt, models.Quiz.id == models.QuizAttempt.quiz_id)\
     .group_by(models.Quiz.id, models.Quiz.title)\
     .order_by(func.avg(models.QuizAttempt.score).asc())\
     .limit(5).all()
    lowest_scoring_quizzes = [
        schemas.QuizStat(quiz_id=qid, quiz_title=title, value=int(avg))
        for qid, title, avg in lowest_scoring_query
    ]

    return schemas.AdminDashboardData(
        stats=stats,
        recent_activity=recent_activity,
        most_attempted_quizzes=most_attempted_quizzes,
        lowest_scoring_quizzes=lowest_scoring_quizzes
    )