"""User management — IT Support approves managers and assigns departments."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_it_support
from ..models import Department, User, UserRole
from ..schemas import AssignDepartments, MessageResponse, UserOut, UserWithDepartments

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserWithDepartments])
def list_users(
    role: Optional[UserRole] = None,
    pending: Optional[bool] = Query(None, description="Filter by approval status"),
    db: Session = Depends(get_db),
    _: User = Depends(require_it_support),
):
    stmt = select(User)
    if role is not None:
        stmt = stmt.where(User.role == role)
    if pending is not None:
        stmt = stmt.where(User.is_approved.is_(not pending))
    stmt = stmt.order_by(User.created_at.desc())
    return db.scalars(stmt).all()


@router.post("/{user_id}/approve", response_model=UserOut)
def approve_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_it_support),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    user.is_approved = True
    user.is_active = True
    db.commit()
    db.refresh(user)
    return user


@router.post("/{user_id}/deactivate", response_model=UserOut)
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_it_support),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if user.id == current.id:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account.")
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user


@router.post("/{user_id}/activate", response_model=UserOut)
def activate_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_it_support),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    user.is_active = True
    db.commit()
    db.refresh(user)
    return user


@router.put("/{user_id}/departments", response_model=UserWithDepartments)
def assign_departments(
    user_id: int,
    payload: AssignDepartments,
    db: Session = Depends(get_db),
    _: User = Depends(require_it_support),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if user.role != UserRole.manager:
        raise HTTPException(status_code=400, detail="Departments can only be assigned to managers.")

    departments = db.scalars(
        select(Department).where(Department.id.in_(payload.department_ids))
    ).all()
    if len(departments) != len(set(payload.department_ids)):
        raise HTTPException(status_code=400, detail="One or more departments were not found.")

    user.departments = list(departments)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", response_model=MessageResponse)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_it_support),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if user.id == current.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account.")
    db.delete(user)
    db.commit()
    return {"detail": "User deleted."}
