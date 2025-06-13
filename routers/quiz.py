from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Quiz, Chapter
from schemas import QuizCreate, QuizRead, QuizUpdate

router = APIRouter(
    prefix="/quizzes",
    tags=["quizzes"]
)

@router.get("/", response_model=list[QuizRead])
def get_all_quizzes(db: Session = Depends(get_db)):
    return db.query(Quiz).all()



@router.post("/", response_model=QuizRead)
def create_quiz(quiz: QuizCreate, db: Session = Depends(get_db)):
    chapter = db.query(Chapter).filter(Chapter.id == quiz.chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    new_quiz = Quiz(
        title=quiz.title,
        chapter_id=quiz.chapter_id
    )
    db.add(new_quiz)
    db.commit()
    db.refresh(new_quiz)
    return new_quiz

@router.get("/{quiz_id}", response_model=QuizRead)
def get_quiz(quiz_id: int, db: Session = Depends(get_db)):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return quiz


@router.put("/{quiz_id}", response_model=QuizRead)
def update_quiz(quiz_id: int, quiz: QuizUpdate, db: Session = Depends(get_db)):
    db_quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not db_quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    db_quiz.title = quiz.title
    db_quiz.chapter_id = quiz.chapter_id
    db.commit()
    db.refresh(db_quiz)
    return db_quiz


@router.delete("/{quiz_id}")
def delete_quiz(quiz_id: int, db: Session = Depends(get_db)):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    db.delete(quiz)
    db.commit()
    return {"message": "Quiz deleted successfully"}



@router.get("/search/")
def search_quizzes(query: str, db: Session = Depends(get_db)):
    return db.query(Quiz).filter(Quiz.title.ilike(f"%{query}%")).all()