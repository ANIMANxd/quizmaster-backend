from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
from pydantic import BaseModel, EmailStr

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="user")  # 'user' or 'admin'
    created_at = Column(DateTime, default=datetime.utcnow)
    attempts = relationship("QuizAttempt", back_populates="user", cascade="all, delete")


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str


class Subject(Base):
    __tablename__ = 'subjects'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String)
    chapters = relationship("Chapter", back_populates="subject", cascade="all, delete")


class Chapter(Base):
    __tablename__ = "chapters"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"))

    subject = relationship("Subject", back_populates="chapters")
    quizzes = relationship("Quiz", back_populates="chapter", cascade="all, delete")


#QUESTIONS TABLE

class Quiz(Base):
    __tablename__ = "quizzes"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False)
    is_ai_generated = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    chapter = relationship("Chapter", back_populates="quizzes")
    questions = relationship("Question", back_populates="quiz", cascade="all, delete")  
    attempts = relationship("QuizAttempt", back_populates="quiz", cascade="all, delete")



class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    question_text = Column(Text, nullable=False)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)  
    marks = Column(Integer, default=1)
    question_type = Column(String, default="mcq")

    quiz = relationship("Quiz", back_populates="questions")
    options = relationship("Option", back_populates="question", cascade="all, delete")



class Option(Base):
    __tablename__ = 'options'
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    option_text = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False)

    question = relationship("Question", back_populates="options")


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    quiz_id = Column(Integer, ForeignKey("quizzes.id"))
    score = Column(Integer)
    attempt_number = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="attempts")
    quiz = relationship("Quiz", back_populates="attempts")

