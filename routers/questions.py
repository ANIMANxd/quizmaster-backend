from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Question, Option, Quiz
from schemas import QuestionCreate, QuestionRead

router = APIRouter(
    prefix="/questions",
    tags=["questions"]
)

@router.post("/", response_model=QuestionRead)
def create_question(question: QuestionCreate, db: Session = Depends(get_db)):
    # Validate quiz exists
    quiz = db.query(Quiz).filter(Quiz.id == question.quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    new_question = Question(
        question_text=question.question_text,
        quiz_id=question.quiz_id,
        marks=question.marks,
        question_type=question.question_type
    )
    db.add(new_question)
    db.commit()
    db.refresh(new_question)

    for opt in question.options:
        db_option = Option(
            question_id=new_question.id,
            option_text=opt.option_text,
            is_correct=opt.is_correct
        )
        db.add(db_option)

    db.commit()
    db.refresh(new_question)
    return new_question


@router.get("/by-quiz/{quiz_id}", response_model=list[QuestionRead])
def get_questions_by_quiz(quiz_id: int, db: Session = Depends(get_db)):
    return db.query(Question).filter(Question.quiz_id == quiz_id).all()
