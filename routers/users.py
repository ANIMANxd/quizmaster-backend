# routers/users.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from models import User
from auth import get_current_user_email, get_current_user
from schemas import LoginResponse, UserCreate, UserResponse
from auth import get_password_hash
from datetime import datetime
from sqlalchemy.exc import IntegrityError



router = APIRouter(
    prefix="/users",
    tags=["users"]
)
@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user

@router.get("/")
def list_users(
    db: Session = Depends(get_db),
    name: str = Query(None),
    role: str = Query(None),
    is_active: bool = Query(None),
    skip: int = 0,
    limit: int = 100
):
    query = db.query(User)

    if name:
        query = query.filter(User.name.ilike(f"%{name}%"))

    if role:
        query = query.filter(User.role == role)

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    users = query.offset(skip).limit(limit).all()
    return users

@router.put("/{user_id}/toggle-active")
def toggle_user_active(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    return {"status": "success", "is_active": user.is_active}

@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()
    return {"status": "deleted"}

@router.post("/addUser")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already exists")

    new_user = User(
        name=user.name,
        email=user.email,
        password_hash=get_password_hash(user.password),
        role=user.role,
        created_at=datetime.utcnow()
    )
    db.add(new_user)
    db.commit()
    db.rollback()
    db.refresh(new_user)
    return {"message": "User created successfully", "user": UserResponse.from_orm(new_user)}


@router.get("/search/")
def search_users(query: str, db: Session = Depends(get_db)):
    return db.query(User).filter(User.name.ilike(f"%{query}%")).all()
