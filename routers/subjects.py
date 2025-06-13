from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Subject
from schemas import SubjectCreate, SubjectOut

router = APIRouter()

@router.get("/", response_model=list[SubjectOut])
def get_all_subjects(db: Session = Depends(get_db)):
    return db.query(Subject).all()

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