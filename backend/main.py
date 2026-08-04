from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import auth, feedback, profile, recommend, user, wardrobe
from backend.utils.dependencies import get_current_user
from database import models  # noqa: F401
from database.connection import Base, engine
from database.models import User


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ASRA AI Styling Recommendation Assistant",
    description="AI智能穿搭推荐助手",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
