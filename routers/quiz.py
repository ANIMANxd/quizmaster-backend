from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List # <--- ADD THIS for List type hint

from database import get_db
# It's better to import the modules directly to avoid confusion
import models
import schemas
from auth import get_current_user

router = APIRouter(
    prefix="/quizzes",
    tags=["quizzes"]
)

@router.get("/", response_model=List[schemas.QuizRead])
def get_all_quizzes(db: Session = Depends(get_db)):
    """
    Gets all quizzes. Intended for admin use.
    """
    db_quizzes = db.query(models.Quiz).all()
    # Using from_orm is cleaner if the schema is correct, which it should be now.
    return [schemas.QuizRead.from_orm(q) for q in db_quizzes]

# ==================== CORRECTED ROUTE ORDER AND LOGIC ====================
# The specific path "/by-teacher" MUST be defined BEFORE the dynamic path "/{quiz_id}".

@router.get("/by-teacher", response_model=List[schemas.QuizRead])
def get_quizzes_for_teacher(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Returns a list of all quizzes that belong to the subjects
    assigned to the currently logged-in teacher.
    """
    if current_user.role != 'teacher':
        raise HTTPException(
            status_code=403, 
            detail="This endpoint is for teachers only."
        )

    teacher_subject_ids = {subject.id for subject in current_user.teacher_subjects}

    if not teacher_subject_ids:
        return []

    db_quizzes = db.query(models.Quiz)\
        .join(models.Chapter, models.Quiz.chapter_id == models.Chapter.id)\
        .filter(models.Chapter.subject_id.in_(teacher_subject_ids))\
        .all()
    
    # from_orm should work correctly now that the pathing issue is solved.
    # This is more efficient than manually building each object.
    return [schemas.QuizRead.from_orm(q) for q in db_quizzes]

# The POST endpoint for creating a quiz
@router.post("/", response_model=schemas.QuizRead)
def create_quiz(
    quiz: schemas.QuizCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    chapter = db.query(models.Chapter).filter(models.Chapter.id == quiz.chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    if current_user.role == "teacher":
        teacher_subject_ids = {s.id for s in current_user.teacher_subjects}
        if chapter.subject_id not in teacher_subject_ids:
            raise HTTPException(
                status_code=403,
                detail="Forbidden: You are not assigned to this subject and cannot create quizzes for it."
            )

    new_quiz = models.Quiz(
        title=quiz.title,
        chapter_id=quiz.chapter_id
        # is_ai_generated will use its default value of False
    )
    db.add(new_quiz)
    db.commit()
    db.refresh(new_quiz)
    return new_quiz

# The SEARCH endpoint should also come before the dynamic ID endpoint.
@router.get("/search/", response_model=List[schemas.QuizRead])
def search_quizzes(query: str, db: Session = Depends(get_db)):
    # This should also return the correct schema
    db_quizzes = db.query(models.Quiz).filter(models.Quiz.title.ilike(f"%{query}%")).all()
    return [schemas.QuizRead.from_orm(q) for q in db_quizzes]


# The dynamic path "/{quiz_id}" must be defined LAST among the GET routes.
@router.get("/{quiz_id}", response_model=schemas.QuizRead)
def get_quiz(quiz_id: int, db: Session = Depends(get_db)):
    quiz = db.query(models.Quiz).filter(models.Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return quiz


@router.put("/{quiz_id}", response_model=schemas.QuizRead)
def update_quiz(quiz_id: int, quiz: schemas.QuizUpdate, db: Session = Depends(get_db)):
    db_quiz = db.query(models.Quiz).filter(models.Quiz.id == quiz_id).first()
    if not db_quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    db_quiz.title = quiz.title
    db_quiz.chapter_id = quiz.chapter_id
    db.commit()
    db.refresh(db_quiz)
    return db_quiz


@router.delete("/{quiz_id}")
def delete_quiz(quiz_id: int, db: Session = Depends(get_db)):
    quiz = db.query(models.Quiz).filter(models.Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    db.delete(quiz)
    db.commit()
    return {"message": "Quiz deleted successfully"}


@router.put("/quizzes/{quiz_id}/questions", response_model=schemas.QuizRead)
def update_quiz_with_questions(
    quiz_id: int,
    questions: List[schemas.QuestionCreate], # We reuse the QuestionCreate schema!
    db: Session = Depends(get_db)
):
    # 1. Get the quiz and its existing questions
    db_quiz = db.query(models.Quiz).options(
        joinedload(models.Quiz.questions).joinedload(models.Question.options)
    ).filter(models.Quiz.id == quiz_id).first()
    
    if not db_quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    # 2. Clear out all old questions and options for this quiz
    # The 'cascade="all, delete"' on your model relationships handles this beautifully.
    for question in db_quiz.questions:
        db.delete(question)
    db.flush() # Execute the deletes

    # 3. Add the new questions and options from the payload
    for q_in in questions:
        new_question = models.Question(
            question_text=q_in.question_text,
            quiz_id=quiz_id,
            marks=q_in.marks,
            question_type=q_in.question_type
        )
        db.add(new_question)
        db.flush() # Get the new_question.id

        for opt_in in q_in.options:
            new_option = models.Option(
                question_id=new_question.id,
                option_text=opt_in.option_text,
                is_correct=opt_in.is_correct
            )
            db.add(new_option)
    
    db.commit()
    db.refresh(db_quiz)
    
    return db_quiz