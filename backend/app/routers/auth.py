"""Authentication: OTP request, signup (manager/member), and login."""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..models import Department, OtpCode, User, UserRole
from ..schemas import (
    DepartmentOut,
    LoginRequest,
    ManagerSignup,
    MemberSignup,
    MessageResponse,
    OtpLoginRequest,
    OtpRequest,
    Token,
    UserOut,
)
from ..security import (
    create_access_token,
    generate_otp,
    hash_otp,
    hash_password,
    verify_otp,
    verify_password,
)
from ..sms import normalize_mobile, send_otp_sms

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _issue_otp(db: Session, mobile: str, purpose: str) -> None:
    """Create and send a fresh OTP, enforcing a resend cooldown."""
    recent = db.scalar(
        select(OtpCode)
        .where(OtpCode.mobile == mobile, OtpCode.purpose == purpose)
        .order_by(OtpCode.created_at.desc())
    )
    if recent:
        age = (_now() - recent.created_at).total_seconds()
        if age < settings.OTP_RESEND_COOLDOWN_SECONDS:
            wait = int(settings.OTP_RESEND_COOLDOWN_SECONDS - age)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Please wait {wait}s before requesting another OTP.",
            )

    code = generate_otp()
    otp = OtpCode(
        mobile=mobile,
        purpose=purpose,
        code_hash=hash_otp(code),
        expires_at=_now() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES),
    )
    db.add(otp)
    db.commit()
    send_otp_sms(mobile, code)


def _consume_otp(db: Session, mobile: str, purpose: str, code: str) -> None:
    """Validate an OTP and mark it used. Raises HTTPException on failure."""
    otp = db.scalar(
        select(OtpCode)
        .where(
            OtpCode.mobile == mobile,
            OtpCode.purpose == purpose,
            OtpCode.is_used.is_(False),
        )
        .order_by(OtpCode.created_at.desc())
    )
    if otp is None:
        raise HTTPException(status_code=400, detail="No active OTP. Please request a new one.")
    if otp.expires_at < _now():
        raise HTTPException(status_code=400, detail="OTP expired. Please request a new one.")
    if otp.attempts >= settings.OTP_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many attempts. Request a new OTP.")

    if not verify_otp(code, otp.code_hash):
        otp.attempts += 1
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid OTP.")

    otp.is_used = True
    db.commit()


@router.post("/request-otp", response_model=MessageResponse)
def request_otp(payload: OtpRequest, db: Session = Depends(get_db)):
    mobile = normalize_mobile(payload.mobile)
    existing = db.scalar(select(User).where(User.mobile == mobile))

    if payload.purpose == "login" and existing is None:
        raise HTTPException(status_code=404, detail="No account found for this mobile number.")
    if payload.purpose == "signup" and existing is not None:
        raise HTTPException(status_code=409, detail="An account already exists for this mobile number.")

    if not settings.REQUIRE_OTP:
        raise HTTPException(status_code=400, detail="OTP verification is currently disabled.")

    _issue_otp(db, mobile, payload.purpose)
    return {"detail": "OTP sent successfully."}


def _verify_signup_otp(db: Session, mobile: str, otp: Optional[str]) -> None:
    """Validate the signup OTP, unless OTP verification is disabled."""
    if not settings.REQUIRE_OTP:
        return
    if not otp:
        raise HTTPException(status_code=400, detail="OTP is required.")
    _consume_otp(db, mobile, "signup", otp)


@router.post("/signup/manager", response_model=Token, status_code=201)
def signup_manager(payload: ManagerSignup, db: Session = Depends(get_db)):
    mobile = normalize_mobile(payload.mobile)
    if db.scalar(select(User).where(User.mobile == mobile)):
        raise HTTPException(status_code=409, detail="An account already exists for this mobile number.")

    _verify_signup_otp(db, mobile, payload.otp)

    user = User(
        name=payload.name.strip(),
        mobile=mobile,
        role=UserRole.manager,
        hashed_password=hash_password(payload.password),
        is_approved=False,  # requires IT Support approval
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    # Managers cannot log in until approved; no token issued.
    return Token(
        access_token="",
        user=UserOut.model_validate(user),
    )


@router.post("/signup/member", response_model=Token, status_code=201)
def signup_member(payload: MemberSignup, db: Session = Depends(get_db)):
    mobile = normalize_mobile(payload.mobile)
    if db.scalar(select(User).where(User.mobile == mobile)):
        raise HTTPException(status_code=409, detail="An account already exists for this mobile number.")
    if db.scalar(select(User).where(User.flat_no == payload.flat_no)):
        raise HTTPException(
            status_code=409,
            detail=f"Flat {payload.flat_no} is already registered. Only one registration per flat is allowed.",
        )

    _verify_signup_otp(db, mobile, payload.otp)

    user = User(
        name=payload.name.strip(),
        mobile=mobile,
        role=UserRole.member,
        flat_no=payload.flat_no,
        hashed_password=hash_password(payload.password),
        is_approved=True,  # members are auto-approved (one per flat)
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(subject=user.id, role=user.role.value)
    return Token(access_token=token, user=UserOut.model_validate(user))


def _login_success(user: User) -> Token:
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Your account has been deactivated.")
    if not user.is_approved:
        raise HTTPException(status_code=403, detail="Account pending approval by IT Support.")
    token = create_access_token(subject=user.id, role=user.role.value)
    return Token(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    mobile = normalize_mobile(payload.mobile)
    user = db.scalar(select(User).where(User.mobile == mobile))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid mobile number or password.")
    return _login_success(user)


@router.post("/login-otp", response_model=Token)
def login_otp(payload: OtpLoginRequest, db: Session = Depends(get_db)):
    mobile = normalize_mobile(payload.mobile)
    user = db.scalar(select(User).where(User.mobile == mobile))
    if user is None:
        raise HTTPException(status_code=404, detail="No account found for this mobile number.")
    _consume_otp(db, mobile, "login", payload.otp)
    return _login_success(user)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/me/departments", response_model=list[DepartmentOut])
def my_departments(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Departments the current user can post to.

    Managers get only their assigned departments; IT Support gets all active ones.
    """
    if current_user.role == UserRole.manager:
        return [d for d in current_user.departments if d.is_active]
    return db.scalars(
        select(Department).where(Department.is_active.is_(True)).order_by(Department.name)
    ).all()
