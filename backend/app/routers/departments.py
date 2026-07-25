"""Department management. IT Support creates/edits; everyone can list."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, require_it_support
from ..models import Department, User
from ..schemas import DepartmentCreate, DepartmentOut, DepartmentUpdate, MessageResponse

router = APIRouter(prefix="/api/departments", tags=["departments"])


@router.get("", response_model=list[DepartmentOut])
def list_departments(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(Department)
    if not include_inactive:
        stmt = stmt.where(Department.is_active.is_(True))
    return db.scalars(stmt.order_by(Department.name)).all()


@router.post("", response_model=DepartmentOut, status_code=201)
def create_department(
    payload: DepartmentCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_it_support),
):
    if db.scalar(select(Department).where(Department.name == payload.name)):
        raise HTTPException(status_code=409, detail="A department with this name already exists.")
    dept = Department(**payload.model_dump())
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept


@router.put("/{dept_id}", response_model=DepartmentOut)
def update_department(
    dept_id: int,
    payload: DepartmentUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_it_support),
):
    dept = db.get(Department, dept_id)
    if dept is None:
        raise HTTPException(status_code=404, detail="Department not found.")
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] != dept.name:
        if db.scalar(select(Department).where(Department.name == data["name"])):
            raise HTTPException(status_code=409, detail="A department with this name already exists.")
    for key, value in data.items():
        setattr(dept, key, value)
    db.commit()
    db.refresh(dept)
    return dept


@router.delete("/{dept_id}", response_model=MessageResponse)
def deactivate_department(
    dept_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_it_support),
):
    dept = db.get(Department, dept_id)
    if dept is None:
        raise HTTPException(status_code=404, detail="Department not found.")
    dept.is_active = False
    db.commit()
    return {"detail": "Department deactivated."}
