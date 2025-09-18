from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(nullable=True)
    first_name: Mapped[str] = mapped_column()
    is_admin: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column()  # Название субботника
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    created_by: Mapped[int] = mapped_column()  # telegram_id админа, который создал

    teams = relationship("Team", back_populates="event")

class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"))

    event = relationship("Event", back_populates="teams")
    scores: Mapped[list["Score"]] = relationship(back_populates="team", cascade="all, delete-orphan")


class Score(Base):
    __tablename__ = "scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    category: Mapped[str] = mapped_column(nullable=False)
    points: Mapped[int] = mapped_column(default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    team: Mapped["Team"] = relationship(back_populates="scores")

