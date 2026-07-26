"""SQLAlchemy ORM models for SocietyHub."""
from __future__ import annotations

import enum
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class UserRole(str, enum.Enum):
    it_support = "it_support"
    manager = "manager"
    member = "member"


class TransactionType(str, enum.Enum):
    credit = "credit"
    debit = "debit"


# Many-to-many: which managers are responsible for which departments.
manager_departments = Table(
    "manager_departments",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "department_id",
        ForeignKey("departments.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    mobile: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # Members only: unique flat identifier (e.g. "A-101").
    flat_no: Mapped[Optional[str]] = mapped_column(
        String(30), unique=True, index=True, nullable=True
    )

    is_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    departments: Mapped[List["Department"]] = relationship(
        secondary=manager_departments, back_populates="managers"
    )
    transactions: Mapped[List["Transaction"]] = relationship(back_populates="created_by")
    broadcasts: Mapped[List["Broadcast"]] = relationship(back_populates="created_by")


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    managers: Mapped[List["User"]] = relationship(
        secondary=manager_departments, back_populates="departments"
    )
    transactions: Mapped[List["Transaction"]] = relationship(back_populates="department")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)  # item / purpose
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)  # money source (credit)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Maintenance Collection department only: per-flat collection details.
    flat_no: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    period_month: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)  # YYYY-MM
    maintenance_amount: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    water_bill: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    due_advance: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)  # + due, - advance
    payment_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    department: Mapped["Department"] = relationship(back_populates="transactions")
    created_by: Mapped["User"] = relationship(back_populates="transactions")


class Broadcast(Base):
    __tablename__ = "broadcasts"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    created_by: Mapped["User"] = relationship(back_populates="broadcasts")


class OtpCode(Base):
    __tablename__ = "otp_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    mobile: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    purpose: Mapped[str] = mapped_column(String(30), nullable=False)  # signup | login
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
