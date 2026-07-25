"""Transactions (credit/debit). Managers post to their departments; all can read."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..deps import get_current_user, require_manager
from ..models import Department, Transaction, TransactionType, User, UserRole
from ..schemas import TransactionCreate, TransactionOut

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


def _serialize(txn: Transaction) -> TransactionOut:
    return TransactionOut(
        id=txn.id,
        department_id=txn.department_id,
        department_name=txn.department.name if txn.department else None,
        type=txn.type,
        title=txn.title,
        amount=float(txn.amount),
        source=txn.source,
        comment=txn.comment,
        created_by_id=txn.created_by_id,
        created_by_name=txn.created_by.name if txn.created_by else None,
        created_at=txn.created_at,
    )


@router.get("", response_model=list[TransactionOut])
def list_transactions(
    department_id: Optional[int] = None,
    type: Optional[TransactionType] = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = (
        select(Transaction)
        .options(joinedload(Transaction.department), joinedload(Transaction.created_by))
        .order_by(Transaction.created_at.desc())
    )
    if department_id is not None:
        stmt = stmt.where(Transaction.department_id == department_id)
    if type is not None:
        stmt = stmt.where(Transaction.type == type)
    stmt = stmt.limit(limit).offset(offset)
    return [_serialize(t) for t in db.scalars(stmt).all()]


@router.post("", response_model=TransactionOut, status_code=201)
def create_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_manager),
):
    dept = db.get(Department, payload.department_id)
    if dept is None or not dept.is_active:
        raise HTTPException(status_code=404, detail="Department not found or inactive.")

    # Managers may only post to departments assigned to them.
    if current.role == UserRole.manager:
        assigned_ids = {d.id for d in current.departments}
        if payload.department_id not in assigned_ids:
            raise HTTPException(
                status_code=403,
                detail="You are not assigned to this department.",
            )

    txn = Transaction(
        department_id=payload.department_id,
        type=payload.type,
        title=payload.title.strip(),
        amount=payload.amount,
        source=payload.source.strip() if payload.source else None,
        comment=payload.comment,
        created_by_id=current.id,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return _serialize(txn)


@router.delete("/{txn_id}", status_code=204)
def delete_transaction(
    txn_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_manager),
):
    txn = db.get(Transaction, txn_id)
    if txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    # A manager may only delete their own entries; IT Support may delete any.
    if current.role == UserRole.manager and txn.created_by_id != current.id:
        raise HTTPException(status_code=403, detail="You can only delete your own entries.")
    db.delete(txn)
    db.commit()
