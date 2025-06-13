from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

import models
import schemas # Assuming your Pydantic schemas are in schemas.py
from database import get_db
from collections import defaultdict
from sqlalchemy.orm import joinedload
from fastapi import Security
from sqlalchemy import func
from datetime import datetime
from .dependencies import require_admin  

router = APIRouter()


# --- Chapter Endpoints ---

@router.get("/chapters/by-subject/{subject_id}", response_model=List[schemas.ChapterRead])
def get_chapters_by_subject(subject_id: int, db: Session = Depends(get_db)):
    """
    Get all chapters for a specific subject.
    This is the endpoint your user dashboard is calling.
    """
    chapters = db.query(models.Chapter).filter(models.Chapter.subject_id == subject_id).all()
    if not chapters:
        # Returning an empty list is better than a 404 for this use case
        return []
    return chapters


# --- Quiz Endpoints ---

@router.get("/quizzes/by-chapter/{chapter_id}", response_model=List[schemas.QuizRead])
def get_quizzes_by_chapter(chapter_id: int, db: Session = Depends(get_db)):
    """
    Get all quizzes (both manual and AI) for a specific chapter.
    This is the endpoint your user dashboard calls.
    """
    quizzes = db.query(models.Quiz).filter(models.Quiz.chapter_id == chapter_id).all()
    if not quizzes:
        return []
    return quizzes


@router.get("/quizzes/{quiz_id}/questions")
def get_quiz_with_questions(quiz_id: int, db: Session = Depends(get_db)):
    """
    This is the most important endpoint for the quiz attempt page.
    It returns a single, complete package of data for a quiz.
    """
    quiz = db.query(models.Quiz).filter(models.Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # The relationships in your models.py do all the heavy lifting here.
    # When you access quiz.questions, SQLAlchemy automatically fetches them.
    
    questions_data = []
    for question in quiz.questions:
        options = question.options # SQLAlchemy fetches these automatically
        
        correct_answers = [opt.option_text for opt in options if opt.is_correct]
        
        questions_data.append({
            "id": question.id,
            "question": question.question_text,
            "type": question.question_type.upper(),
            "marks": question.marks,
            "options": [opt.option_text for opt in options],
            "correct_answers": correct_answers,
        })
    
    return {
        "quiz_id": quiz.id,
        "title": quiz.title,
        "questions": questions_data
    }


# --- Quiz Attempt Endpoints ---

@router.post("/quiz-attempts/", response_model=schemas.QuizAttemptRead)
def create_quiz_attempt(attempt: schemas.QuizAttemptCreate, db: Session = Depends(get_db)):
    """
    Creates a new attempt in the unified 'quiz_attempts' table.
    """
    # Check for existing attempts
    existing_attempts = db.query(models.QuizAttempt).filter(
        models.QuizAttempt.user_id == attempt.user_id,
        models.QuizAttempt.quiz_id == attempt.quiz_id
    ).count()

    if existing_attempts >= 3:
        raise HTTPException(status_code=403, detail="Maximum number of 3 attempts reached.")

    db_attempt = models.QuizAttempt(
        **attempt.dict(),
        attempt_number=existing_attempts + 1
    )
    db.add(db_attempt)
    db.commit()
    db.refresh(db_attempt)
    return db_attempt


@router.get("/quiz-attempts/by-user-quiz/{user_id}/{quiz_id}", response_model=List[schemas.QuizAttemptRead])
def get_attempts_for_user_on_quiz(user_id: int, quiz_id: int, db: Session = Depends(get_db)):
    """
    Gets all attempts a specific user has made on a specific quiz.
    """
    attempts = db.query(models.QuizAttempt).filter(
        models.QuizAttempt.user_id == user_id,
        models.QuizAttempt.quiz_id == quiz_id
    ).order_by(models.QuizAttempt.attempt_number).all()
    
    if not attempts:
        return []
    return attempts

@router.get("/quiz-attempts/by-user/{user_id}", response_model=List[schemas.QuizAttemptRead])
def get_all_attempts_for_user(user_id: int, db: Session = Depends(get_db)):
    """
    Gets all quiz attempts for a single user, ordered by most recent first.
    This is for the user's main history page.
    """
    attempts = db.query(models.QuizAttempt).filter(
        models.QuizAttempt.user_id == user_id
    ).order_by(models.QuizAttempt.timestamp.desc()).all()
    
    return attempts


@router.post("/quiz-attempts/request-reattempt")
def request_reattempt(payload: dict):
    """
    DUMMY ENDPOINT: In a real system, this would log the request for an admin.
    For now, it just simulates the action.
    """
    user_id = payload.get("user_id")
    quiz_id = payload.get("quiz_id")
    print(f"Received re-attempt request from User ID: {user_id} for Quiz ID: {quiz_id}")
    
    # In a real app, you would save this to a 'requests' table in the DB.
    
    return {"message": "Your request for a re-attempt has been sent to the administrator."}


@router.get("/performance/user/{user_id}", response_model=schemas.UserPerformance, tags=["Performance"])
def get_user_performance_summary(user_id: int, db: Session = Depends(get_db)):
    """
    Gathers all performance data for a given user and calculates statistics.
    """
    attempts = db.query(models.QuizAttempt).options(
        joinedload(models.QuizAttempt.quiz).joinedload(models.Quiz.chapter).joinedload(models.Chapter.subject)
    ).filter(models.QuizAttempt.user_id == user_id).all()

    if not attempts:
        return schemas.UserPerformance(
            total_quizzes_taken=0, total_attempts=0, average_score=0.0,
            best_subject=None, worst_subject=None, performance_by_subject=[],
            recent_attempts=[], best_performing_quizzes=[], improvement_areas=[]
        )

    total_attempts = len(attempts)
    total_quizzes_taken = len(set(a.quiz_id for a in attempts))
    average_score = sum(a.score for a in attempts) / total_attempts if total_attempts > 0 else 0

    subject_scores = defaultdict(lambda: {'scores': [], 'count': 0})
    for attempt in attempts:
        subject_name = attempt.quiz.chapter.subject.name
        subject_scores[subject_name]['scores'].append(attempt.score)
        subject_scores[subject_name]['count'] += 1

    performance_by_subject = [
        schemas.PerformanceBySubject(subject_name=name, average_score=sum(data['scores']) / data['count'], attempts_count=data['count'])
        for name, data in subject_scores.items()
    ]
    
    best_subject, worst_subject = None, None
    if performance_by_subject:
        sorted_subjects = sorted(performance_by_subject, key=lambda x: x.average_score)
        best_subject = sorted_subjects[-1].subject_name
        worst_subject = sorted_subjects[0].subject_name
        
    quiz_scores = defaultdict(list)
    for attempt in attempts:
        quiz_scores[attempt.quiz_id].append(attempt.score)
    
    quiz_best_scores = [
        {"quiz_id": quiz_id, "quiz_title": db.query(models.Quiz.title).filter(models.Quiz.id == quiz_id).scalar(), "best_score": max(scores)}
        for quiz_id, scores in quiz_scores.items()
    ]
            
    sorted_quizzes = sorted(quiz_best_scores, key=lambda x: x['best_score'], reverse=True)
    best_performing_quizzes = sorted_quizzes[:5]
    improvement_areas = sorted(quiz_best_scores, key=lambda x: x['best_score'])[:5]

    recent_attempts_query = sorted(attempts, key=lambda x: x.timestamp, reverse=True)[:10]
    recent_attempts = [
        schemas.RecentAttempt(quiz_title=a.quiz.title, score=a.score, timestamp=a.timestamp)
        for a in recent_attempts_query
    ]

    return schemas.UserPerformance(
        total_quizzes_taken=total_quizzes_taken, total_attempts=total_attempts, average_score=average_score,
        performance_by_subject=sorted(performance_by_subject, key=lambda x: x.average_score, reverse=True),
        recent_attempts=list(reversed(recent_attempts)), best_subject=best_subject, worst_subject=worst_subject,
        best_performing_quizzes=best_performing_quizzes, improvement_areas=improvement_areas
    )


@router.get("/users", response_model=List[schemas.UserResponse])
def get_all_users(
    admin: models.User = Security(require_admin),
    db: Session = Depends(get_db)
):
    """Get a list of all users. Only accessible by admins."""
    users = db.query(models.User).all()
    return users

# (Add your other user management endpoints here like delete, add, etc.,
#  all protected with `Security(require_admin)`)


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