from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Chapter, Subject
from schemas import ChapterCreate, ChapterRead

router = APIRouter(
    prefix="/chapters",
    tags=["chapters"]
)

@router.get("/", response_model=list[ChapterRead])
def get_all_chapters(db: Session = Depends(get_db)):
    return db.query(Chapter).all()


@router.post("/", response_model=ChapterRead)
def create_chapter(chapter: ChapterCreate, db: Session = Depends(get_db)):
    subject = db.query(Subject).filter(Subject.id == chapter.subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    new_chapter = Chapter(
        name=chapter.name,
        subject_id=chapter.subject_id
    )
    db.add(new_chapter)
    db.commit()
    db.refresh(new_chapter)
    return new_chapter


@router.put("/{chapter_id}", response_model=ChapterRead)
def update_chapter(chapter_id: int, updated_data: ChapterCreate, db: Session = Depends(get_db)):
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    chapter.name = updated_data.name
    chapter.subject_id = updated_data.subject_id
    db.commit()
    db.refresh(chapter)
    return chapter


@router.delete("/{chapter_id}")
def delete_chapter(chapter_id: int, db: Session = Depends(get_db)):
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    db.delete(chapter)
    db.commit()
    return {"status": "deleted"}



@router.get("/search/")
def search_chapters(query: str, db: Session = Depends(get_db)):
    return db.query(Chapter).filter(Chapter.name.ilike(f"%{query}%")).all()