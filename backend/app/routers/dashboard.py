"""Dashboard summary: society-wide and per-department credit/debit totals."""
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..deps import get_current_user
from ..models import Broadcast, Department, Transaction, TransactionType, User
from ..schemas import DashboardSummary, DepartmentSummary
from .broadcasts import _serialize as serialize_broadcast
from .transactions import _serialize as serialize_txn

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    # Aggregate credit/debit per department in a single grouped query.
    rows = db.execute(
        select(
            Transaction.department_id,
            Transaction.type,
            func.coalesce(func.sum(Transaction.amount), 0),
        ).group_by(Transaction.department_id, Transaction.type)
    ).all()

    credit_by_dept: dict[int, float] = {}
    debit_by_dept: dict[int, float] = {}
    for dept_id, txn_type, total in rows:
        total = float(total)
        if txn_type == TransactionType.credit:
            credit_by_dept[dept_id] = total
        else:
            debit_by_dept[dept_id] = total

    departments = db.scalars(
        select(Department).where(Department.is_active.is_(True)).order_by(Department.name)
    ).all()

    dept_summaries: list[DepartmentSummary] = []
    total_credit = 0.0
    total_debit = 0.0
    for d in departments:
        credit = credit_by_dept.get(d.id, 0.0)
        debit = debit_by_dept.get(d.id, 0.0)
        total_credit += credit
        total_debit += debit
        dept_summaries.append(
            DepartmentSummary(
                id=d.id,
                name=d.name,
                description=d.description,
                icon=d.icon,
                is_active=d.is_active,
                total_credit=credit,
                total_debit=debit,
                balance=credit - debit,
            )
        )

    recent_txns = db.scalars(
        select(Transaction)
        .options(joinedload(Transaction.department), joinedload(Transaction.created_by))
        .order_by(Transaction.created_at.desc())
        .limit(10)
    ).all()

    recent_broadcasts = db.scalars(
        select(Broadcast)
        .options(joinedload(Broadcast.created_by))
        .order_by(Broadcast.created_at.desc())
        .limit(5)
    ).all()

    return DashboardSummary(
        total_credit=total_credit,
        total_debit=total_debit,
        balance=total_credit - total_debit,
        department_count=len(departments),
        departments=dept_summaries,
        recent_transactions=[serialize_txn(t) for t in recent_txns],
        recent_broadcasts=[serialize_broadcast(b) for b in recent_broadcasts],
    )
