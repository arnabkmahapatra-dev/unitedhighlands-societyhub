"""Pydantic request/response schemas (Python 3.9 compatible typing)."""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import TransactionType, UserRole


# ---------- Auth / OTP ----------
class OtpRequest(BaseModel):
    mobile: str = Field(..., min_length=6, max_length=20)
    purpose: str = Field("signup", pattern="^(signup|login)$")


class MessageResponse(BaseModel):
    detail: str


class ManagerSignup(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    mobile: str = Field(..., min_length=6, max_length=20)
    otp: Optional[str] = Field(None, max_length=8)
    password: str = Field(..., min_length=8, max_length=128)


class MemberSignup(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    mobile: str = Field(..., min_length=6, max_length=20)
    flat_no: str = Field(..., min_length=1, max_length=30)
    otp: Optional[str] = Field(None, max_length=8)
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("flat_no")
    @classmethod
    def strip_flat(cls, v: str) -> str:
        return v.strip().upper()


class LoginRequest(BaseModel):
    mobile: str = Field(..., min_length=6, max_length=20)
    password: str = Field(..., min_length=1, max_length=128)


class OtpLoginRequest(BaseModel):
    mobile: str = Field(..., min_length=6, max_length=20)
    otp: str = Field(..., min_length=4, max_length=8)


# ---------- Departments ----------
class DepartmentBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    description: Optional[str] = Field(None, max_length=255)
    icon: Optional[str] = Field(None, max_length=60)


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    description: Optional[str] = Field(None, max_length=255)
    icon: Optional[str] = Field(None, max_length=60)
    is_active: Optional[bool] = None


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    is_active: bool


class DepartmentSummary(DepartmentOut):
    total_credit: float = 0.0
    total_debit: float = 0.0
    balance: float = 0.0


# ---------- Users ----------
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    mobile: str
    email: Optional[str] = None
    role: UserRole
    flat_no: Optional[str] = None
    is_approved: bool
    is_active: bool
    created_at: datetime


class UserWithDepartments(UserOut):
    departments: List[DepartmentOut] = []


class AssignDepartments(BaseModel):
    department_ids: List[int]


# ---------- Auth token ----------
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Transactions ----------
class TransactionCreate(BaseModel):
    department_id: int
    type: TransactionType
    title: str = Field(..., min_length=1, max_length=160)
    amount: Decimal = Field(..., gt=0)
    source: Optional[str] = Field(None, max_length=160)
    comment: Optional[str] = None


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    department_id: int
    department_name: Optional[str] = None
    type: TransactionType
    title: str
    amount: float
    source: Optional[str] = None
    comment: Optional[str] = None
    created_by_id: int
    created_by_name: Optional[str] = None
    created_at: datetime


# ---------- Broadcasts ----------
class BroadcastCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=160)
    message: str = Field(..., min_length=2)


class BroadcastOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    message: str
    created_by_id: int
    created_by_name: Optional[str] = None
    created_at: datetime


# ---------- Dashboard ----------
class DashboardSummary(BaseModel):
    total_credit: float
    total_debit: float
    balance: float
    department_count: int
    departments: List[DepartmentSummary]
    recent_transactions: List[TransactionOut]
    recent_broadcasts: List[BroadcastOut]
