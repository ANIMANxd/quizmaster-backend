from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Subject, User
from schemas import SubjectCreate, SubjectOut, UserResponse
from typing import List
from auth import get_current_user

router = APIRouter()

@router.get("/", response_model=list[SubjectOut])
def get_all_subjects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # Add dependency
):
    """
    Lists subjects based on user role:
    - Admin: Sees all subjects.
    - Teacher: Sees only their assigned subjects.
    - Student ('user'): Sees only their assigned subjects.
    """
    if current_user.role == "admin":
        return db.query(Subject).all()
    
    if current_user.role == "teacher":
        # The relationship we defined in py makes this easy!
        return current_user.teacher_subjects

    if current_user.role == "user":
        return current_user.student_subjects
    
    return [] # Should not happen, but good practice

@router.post("/", response_model=SubjectOut)
def create_subject(subject: SubjectCreate, db: Session = Depends(get_db)):
    new_subject = Subject(name=subject.name, description=subject.description)
    db.add(new_subject)
    db.commit()
    db.refresh(new_subject)
    return new_subject

@router.get("/{subject_id}", response_model=SubjectOut)
def get_subject(subject_id: int, db: Session = Depends(get_db)):
    subject = db.query(Subject).get(subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    return subject

@router.put("/{subject_id}", response_model=SubjectOut)
def update_subject(subject_id: int, updated: SubjectCreate, db: Session = Depends(get_db)):
    subject = db.query(Subject).get(subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    subject.name = updated.name
    subject.description = updated.description
    db.commit()
    db.refresh(subject)
    return subject

@router.delete("/{subject_id}")
def delete_subject(subject_id: int, db: Session = Depends(get_db)):
    subject = db.query(Subject).get(subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    db.delete(subject)
    db.commit()
    return {"detail": "Subject deleted"}


@router.get("/search/")
def search_subjects(query: str, db: Session = Depends(get_db)):
    return db.query(Subject).filter(Subject.name.ilike(f"%{query}%")).all()


@router.get("/{subject_id}/students", response_model=List[UserResponse])
def get_students_for_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # The teacher making the request
):
    """
    For a teacher, gets a list of students assigned to one of their subjects.
    An admin can also use this.
    """
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    if current_user.role == 'teacher':
        # Security check: ensure the teacher is actually assigned to this subject
        teacher_subject_ids = {s.id for s in current_user.teacher_subjects}
        if subject_id not in teacher_subject_ids:
            raise HTTPException(status_code=403, detail="You are not authorized to view students for this subject.")
    
    # The 'students' relationship on the Subject model does all the work!
    return subject.students