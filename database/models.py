from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from database.connection import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)

    wardrobes = relationship(
        "Wardrobe",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    profile = relationship(
        "UserProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    feedbacks = relationship(
        "RecommendationFeedback",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    histories = relationship(
        "RecommendationHistory",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Wardrobe(Base):
    __tablename__ = "wardrobes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    category = Column(String(50))
    color = Column(String(50))
    season = Column(String(50))
    style = Column(String(50))
    color_tags = Column(JSON, default=list)
    style_tags = Column(JSON, default=list)
    fit_tags = Column(JSON, default=list)
    occasion_tags = Column(JSON, default=list)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    user = relationship("User", back_populates="wardrobes")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        unique=True,
        nullable=False,
        index=True,
    )
    style = Column(String(50))
    favorite_color = Column(String(50))
    favorite_colors = Column(JSON, default=list)
    style_tags = Column(JSON, default=list)
    fit_tags = Column(JSON, default=list)
    avoid_colors = Column(JSON, default=list)
    occasion_preferences = Column(JSON, default=list)
    body_type = Column(String(50))
    season = Column(String(50))

    user = relationship("User", back_populates="profile")


class EventLog(Base):
    __tablename__ = "event_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    payload = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RecommendationFeedback(Base):
    __tablename__ = "recommendation_feedback"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    feedback_type = Column(String(20), nullable=False)
    outfit_score = Column(Integer, default=0)
    outfit_snapshot = Column(JSON, default=dict)
    reason = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="feedbacks")


class RecommendationHistory(Base):
    __tablename__ = "recommendation_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    request_context = Column(JSON, default=dict)
    response_snapshot = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="histories")
