from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import Base, engine
from routers import auth
from routers import users
from routers.subjects import router as subjects_router
from routers import quiz
from routers import chapters
from routers import questions
from routers import quiz_attempts
from routers import ai_quiz
from routers import quiz_routes
from routers import admin_routes




Base.metadata.create_all(bind=engine)

app = FastAPI(title="QuizMaster Pro")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(users.router)
app.include_router(subjects_router, prefix="/subjects", tags=["Subjects"])
app.include_router(quiz.router)
app.include_router(chapters.router)
app.include_router(questions.router)
app.include_router(quiz_attempts.router)
app.include_router(ai_quiz.router)
app.include_router(quiz_routes.router)
app.include_router(admin_routes.router, prefix="/admin", tags=["Admin Only"])



@app.get("/")
def read_root():
    return {"message": "QuizMaster Pro API is running"}

