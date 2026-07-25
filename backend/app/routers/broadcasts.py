"""Society-wide broadcast updates. Managers & IT Support post; everyone reads."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..deps import get_current_user, require_manager
from ..models import Broadcast, User, UserRole
from ..schemas import BroadcastCreate, BroadcastOut

router = APIRouter(prefix="/api/broadcasts", tags=["broadcasts"])


def _serialize(b: Broadcast) -> BroadcastOut:
    return BroadcastOut(
        id=b.id,
        title=b.title,
        message=b.message,
        created_by_id=b.created_by_id,
        created_by_name=b.created_by.name if b.created_by else None,
        created_at=b.created_at,
    )


@router.get("", response_model=list[BroadcastOut])
def list_broadcasts(
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = (
        select(Broadcast)
        .options(joinedload(Broadcast.created_by))
        .order_by(Broadcast.created_at.desc())
        .limit(limit)
    )
    return [_serialize(b) for b in db.scalars(stmt).all()]


@router.post("", response_model=BroadcastOut, status_code=201)
def create_broadcast(
    payload: BroadcastCreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_manager),
):
    b = Broadcast(
        title=payload.title.strip(),
        message=payload.message.strip(),
        created_by_id=current.id,
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return _serialize(b)


@router.delete("/{broadcast_id}", status_code=204)
def delete_broadcast(
    broadcast_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_manager),
):
    b = db.get(Broadcast, broadcast_id)
    if b is None:
        raise HTTPException(status_code=404, detail="Broadcast not found.")
    if current.role == UserRole.manager and b.created_by_id != current.id:
        raise HTTPException(status_code=403, detail="You can only delete your own broadcasts.")
    db.delete(b)
    db.commit()
