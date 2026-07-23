from sqlalchemy.orm import Session

from app.core.permissions import ROLE_PERMISSIONS
from app.core.security import hash_password
from app.models import ReasonCode, Role, User
from app.services.seed_data import REASON_CODES_SEED


def seed_roles(db: Session) -> None:
    for name, permissions in ROLE_PERMISSIONS.items():
        role = db.query(Role).filter(Role.name == name).first()
        if not role:
            role = Role(name=name, description=f"Papel {name}", permissions=permissions)
            db.add(role)
        else:
            role.permissions = permissions
    db.commit()


def seed_reason_codes(db: Session) -> None:
    for code, category, label, description, requires_comment in REASON_CODES_SEED:
        existing = db.query(ReasonCode).filter(ReasonCode.code == code).first()
        if not existing:
            db.add(
                ReasonCode(
                    code=code,
                    category=category,
                    label=label,
                    description=description,
                    requires_comment=requires_comment,
                    is_active=True,
                )
            )
    db.commit()


def seed_admin_user(db: Session, email: str, password: str, name: str) -> User | None:
    if db.query(User).filter(User.email == email).first():
        return None
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if not admin_role:
        raise RuntimeError("Papel admin não encontrado. Execute seed_roles primeiro.")
    user = User(
        email=email,
        name=name,
        password_hash=hash_password(password),
        role_id=admin_role.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def run_initial_seed(db: Session, admin_email: str, admin_password: str, admin_name: str) -> None:
    seed_roles(db)
    seed_reason_codes(db)
    seed_admin_user(db, admin_email, admin_password, admin_name)
