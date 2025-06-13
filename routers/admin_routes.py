from fastapi import APIRouter, Depends, HTTPException, Security
from sqlalchemy.orm import Session
from typing import List
from collections import defaultdict
from sqlalchemy import func

import models
import schemas
from database import get_db
from .dependencies import require_admin  
from .auth import get_password_hash 

router = APIRouter(prefix="/admin", tags=["Admin Only"])




@router.get("/users", response_model=List[schemas.UserResponse])
def get_all_users(
    admin: models.User = Security(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get a list of all users. Only accessible by admins.
    """
    users = db.query(models.User).all()
    return users


@router.post("/users", response_model=schemas.UserResponse, status_code=201)
def create_user_by_admin(
    user: schemas.UserCreate,
    admin: models.User = Security(require_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new user. Can be 'user' or 'admin' role. Only accessible by admins.
    """
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    new_user = models.User(
        name=user.name,
        email=user.email,
        password_hash=hashed_password,
        role=user.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.delete("/users/{user_id}", status_code=204)
def delete_user_by_admin(
    user_id: int,
    admin: models.User = Security(require_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a user by their ID. Only accessible by admins.
    """
    user_to_delete = db.query(models.User).filter(models.User.id == user_id).first()
    if not user_to_delete:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user_to_delete.role == 'admin' and user_to_delete.id == admin.id:
        raise HTTPException(status_code=403, detail="Admin cannot delete their own account.")

    db.delete(user_to_delete)
    db.commit()
    return


# --- ADMIN DASHBOARD ENDPOINT ---

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