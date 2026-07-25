"""Seed the database with the IT Support account and default departments."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .models import Department, User, UserRole
from .security import hash_password
from .sms import normalize_mobile

# Default departments derived from the society's maintenance expense sheet,
# plus common apartment-society heads. icon = Bootstrap Icons name.
DEFAULT_DEPARTMENTS: list[dict] = [
    {"name": "Security", "icon": "shield-check", "description": "24x7 security manpower & contracts"},
    {"name": "Housekeeping", "icon": "brush", "description": "Cleaning staff wages & services"},
    {"name": "Electricity (Common Area)", "icon": "lightning-charge", "description": "BESCOM / common area power bills"},
    {"name": "STP Vendor", "icon": "droplet", "description": "Sewage treatment plant operations"},
    {"name": "Water Tanker", "icon": "truck", "description": "Bulk water supply"},
    {"name": "Plumber", "icon": "wrench", "description": "Plumbing labour & repairs"},
    {"name": "Gardener", "icon": "flower1", "description": "Landscaping & garden upkeep"},
    {"name": "Electrician", "icon": "plug", "description": "Electrical labour & repairs"},
    {"name": "Pest Control", "icon": "bug", "description": "Pest control services"},
    {"name": "Diesel for DG", "icon": "fuel-pump", "description": "Diesel for backup generators"},
    {"name": "DG Annual AMC", "icon": "gear", "description": "Generator annual maintenance contract"},
    {"name": "Garbage Collection", "icon": "trash", "description": "Waste segregation & disposal"},
    {"name": "Housekeeping Material", "icon": "bucket", "description": "Cleaning consumables"},
    {"name": "Plumbing & Electrical Material", "icon": "tools", "description": "Repair materials"},
    {"name": "Lift / Elevator AMC", "icon": "arrows-vertical", "description": "Elevator maintenance contract"},
    {"name": "Gym Maintenance", "icon": "heart-pulse", "description": "Gym equipment upkeep"},
    {"name": "CCTV & Security Systems", "icon": "camera-video", "description": "Surveillance systems"},
    {"name": "Fire Safety", "icon": "fire", "description": "Fire safety equipment & AMC"},
    {"name": "Maintenance Collection", "icon": "cash-coin", "description": "Monthly maintenance income from flats"},
    {"name": "Miscellaneous", "icon": "three-dots", "description": "Other / uncategorised expenses"},
]


def seed_admin(db: Session) -> None:
    mobile = normalize_mobile(settings.DEFAULT_ADMIN_MOBILE)
    existing = db.scalar(select(User).where(User.mobile == mobile))
    if existing:
        return
    admin = User(
        name=settings.DEFAULT_ADMIN_NAME,
        mobile=mobile,
        role=UserRole.it_support,
        hashed_password=hash_password(settings.DEFAULT_ADMIN_PASSWORD),
        is_approved=True,
        is_active=True,
    )
    db.add(admin)
    db.commit()


def seed_departments(db: Session) -> None:
    if db.scalar(select(Department).limit(1)):
        return
    for d in DEFAULT_DEPARTMENTS:
        db.add(Department(name=d["name"], icon=d["icon"], description=d["description"]))
    db.commit()


def run_seed(db: Session) -> None:
    seed_admin(db)
    seed_departments(db)
