from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, ForeignKey, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

# SQLite database - use data/ directory for Docker volume persistence
# Falls back to current directory for local development
db_path = "./data/spaans_leren.db" if os.path.exists("./data") else "./spaans_leren.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Word(Base):
    __tablename__ = "words"

    id = Column(Integer, primary_key=True, index=True)
    dutch_word = Column(String, index=True, nullable=False)
    spanish_word = Column(String, index=True, nullable=False)
    category = Column(String, default="algemeen")
    mnemonic_text = Column(Text)  # Tekstuele geheugensteun
    mnemonic_image = Column(Text)  # Base64 encoded image of SVG
    conjugations = Column(Text)  # JSON string voor werkwoordvervoegingen
    forms = Column(Text)  # JSON string voor meervoud/geslacht vormen

    # Learning enhancement fields
    example_sentences = Column(Text)  # JSON: [{"spanish": "...", "dutch": "...", "difficulty": "..."}]
    related_words = Column(Text)  # JSON: {"synonyms": [...], "antonyms": [...], "family": [...]}
    grammar_tips = Column(Text)  # JSON: {"usage_rules": [...], "common_mistakes": [...], "tips": [...]}
    video_url = Column(String)  # Optional YouTube embed URL

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Spaced Repetition fields (SM-2 algorithm)
    review_count = Column(Integer, default=0)  # Total times reviewed
    correct_count = Column(Integer, default=0)  # Times answered correctly (quality >= 3)
    easiness_factor = Column(Float, default=2.5)  # SM-2 easiness factor (1.3 - 2.5+)
    interval = Column(Integer, default=0)  # Days until next review
    repetitions = Column(Integer, default=0)  # Consecutive correct reviews
    last_reviewed = Column(DateTime, nullable=True)  # Last review timestamp
    next_review = Column(DateTime, default=datetime.utcnow, index=True)  # When to review next

    # Relationship
    review_history = relationship("ReviewHistory", back_populates="word", cascade="all, delete-orphan")


class ReviewHistory(Base):
    """Track individual review sessions for each word"""
    __tablename__ = "review_history"

    id = Column(Integer, primary_key=True, index=True)
    word_id = Column(Integer, ForeignKey("words.id"), nullable=False, index=True)
    reviewed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    quality = Column(Integer, nullable=False)  # 0-5 (SM-2: 0=Again, 3=Hard, 4=Good, 5=Easy)
    interval_before = Column(Integer)  # Interval before this review
    interval_after = Column(Integer)  # Interval after this review
    easiness_factor_after = Column(Float)  # EF after this review

    # Relationship
    word = relationship("Word", back_populates="review_history")


class StudySession(Base):
    """Track daily study sessions for streak tracking and heatmap"""
    __tablename__ = "study_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_date = Column(Date, nullable=False, unique=True, index=True)  # Date of session (no time)
    cards_reviewed = Column(Integer, default=0)  # Number of cards reviewed this day
    session_duration_minutes = Column(Integer, default=0)  # Total session time
    created_at = Column(DateTime, default=datetime.utcnow)

# Create tables
def init_db():
    Base.metadata.create_all(bind=engine)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
