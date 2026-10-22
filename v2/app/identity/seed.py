from sqlalchemy.orm import Session

from app.identity import public as identity_public
from app.identity.models import Role, User

E2E_OPERATOR_PASSWORD = "ensaio123"


def ensure_seed(db: Session, *, email: str, password: str, name: str) -> None:
    identity_public.ensure_admin_user(db, email, password, name)


def ensure_e2e_operator_users(db: Session, *, password: str = E2E_OPERATOR_PASSWORD) -> None:
    """Comprador/aduana/estoque só em epic_v2_test (e2e_prepare). Nunca no boot de operação."""
    identity_public.ensure_comprador_role(db)
    identity_public.ensure_aduana_role(db)
    identity_public.ensure_estoque_role(db)
    specs = (
        ("comprador@epic.com.br", "Comprador ensaio", "comprador"),
        ("aduana@epic.com.br", "Aduana ensaio", "aduana"),
        ("estoque@epic.com.br", "Estoque ensaio", "estoque"),
    )
    for email, name, role_name in specs:
        if db.query(User).filter(User.email == email).first():
            continue
        role = db.query(Role).filter(Role.name == role_name).first()
        if role is None:
            raise RuntimeError(f"papel {role_name} ausente após ensure_*_role")
        identity_public.create_user(
            db,
            email=email,
            name=name,
            password=password,
            role_id=role.id,
            is_active=True,
        )
