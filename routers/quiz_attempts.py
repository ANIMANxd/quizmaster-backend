from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import QuizAttempt
from schemas import QuizAttemptCreate, QuizAttemptRead
from sqlalchemy.orm import joinedload
from typing import List
from models import Quiz, Chapter, Subject
from datetime import datetime


router = APIRouter(prefix="/quiz_attempts", tags=["Quiz Attempts"])

@router.post("/", response_model=QuizAttemptRead)
@router.post("/", response_model=QuizAttemptRead)
def submit_attempt(attempt: QuizAttemptCreate, db: Session = Depends(get_db)):
    try:
        existing_attempts = db.query(QuizAttempt).filter_by(
            user_id=attempt.user_id,
            quiz_id=attempt.quiz_id
        ).count()

        if existing_attempts >= 3:
            raise HTTPException(status_code=403, detail="Maximum 3 attempts allowed.")

        new_attempt = QuizAttempt(
            user_id=attempt.user_id,
            quiz_id=attempt.quiz_id,
            score=attempt.score,
            attempt_number=existing_attempts + 1
        )
        db.add(new_attempt)
        db.commit()
        db.refresh(new_attempt)
        return new_attempt
    except Exception as e:
        print("Error submitting quiz attempt:", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/{quiz_id}", response_model=List[QuizAttemptRead])
def get_attempts_for_quiz_by_user(user_id: int, quiz_id: int, db: Session = Depends(get_db)):
    attempts = db.query(QuizAttempt).filter(
        QuizAttempt.user_id == user_id,
        QuizAttempt.quiz_id == quiz_id
    ).order_by(QuizAttempt.attempt_number).all()
    return attempts

@router.get("/{user_id}", response_model=List[QuizAttemptRead])
def get_all_attempts_for_user(user_id: int, db: Session = Depends(get_db)):
    attempts = db.query(QuizAttempt)\
        .options(
            joinedload(QuizAttempt.quiz).joinedload(Quiz.chapter).joinedload(Chapter.subject)
        ).filter(QuizAttempt.user_id == user_id).all()
    return attempts

