from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.routers import agent, auth, chat, evaluation, feedback, history, memory, profile, recommend, user, wardrobe
from backend.core.config import BASE_DIR, settings
from backend.utils.dependencies import get_current_user
from database import models  # noqa: F401
from database.models import User


app = FastAPI(
    title="ASRA AI Styling Recommendation Assistant",
    description="AI智能穿搭推荐助手",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user.router)
app.include_router(auth.router)
app.include_router(wardrobe.router)
app.include_router(recommend.router)
app.include_router(profile.router)
app.include_router(feedback.router)
app.include_router(history.router)
app.include_router(evaluation.router)
app.include_router(agent.router)
app.include_router(memory.router)
app.include_router(chat.router)

frontend_dir = BASE_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/app", StaticFiles(directory=frontend_dir, html=True), name="frontend")

uploads_dir = BASE_DIR / "uploads"
if uploads_dir.exists():
    app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")


@app.get("/")
def home():
    return {
        "project": "ASRA",
        "message": "AI Styling Recommendation Assistant",
        "status": "success",
    }


@app.get("/test/user")
def test_user(current_user: User = Depends(get_current_user)):
    return {"username": current_user.username, "email": current_user.email}
