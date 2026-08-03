"""I5-5 — papéis operacionais aduana / estoque (seed Identity)."""

from __future__ import annotations

import json

from app.identity import public as identity_public
from app.identity.models import Role


def test_aduana_estoque_permission_constants():
    assert set(identity_public.ADUANA_PERMISSIONS) == {
        "customs:read",
        "customs:write",
        "customs:clear",
        "documents:read",
        "documents:write",
        "audit:read",
    }
    assert set(identity_public.ESTOQUE_PERMISSIONS) == {
        "inventory:read",
        "inventory:write",
        "inventory:adjust",
        "documents:read",
        "audit:read",
    }
    # Não diluir comprador com write operacional dedicado
    assert "customs:write" not in identity_public.COMPRADOR_PERMISSIONS
    assert "inventory:write" not in identity_public.COMPRADOR_PERMISSIONS
    for perm in ("customs:read", "customs:write", "customs:clear"):
        assert perm in identity_public.ADMIN_PERMISSIONS
    for perm in ("inventory:read", "inventory:write", "inventory:adjust"):
        assert perm in identity_public.ADMIN_PERMISSIONS


def test_ensure_aduana_estoque_roles(db):
    aduana = identity_public.ensure_aduana_role(db)
    estoque = identity_public.ensure_estoque_role(db)
    db.commit()

    assert aduana.name == "aduana"
    assert estoque.name == "estoque"
    assert json.loads(aduana.permissions_json) == identity_public.ADUANA_PERMISSIONS
    assert json.loads(estoque.permissions_json) == identity_public.ESTOQUE_PERMISSIONS

    # Idempotente + atualiza matriz se divergir
    aduana.permissions_json = json.dumps(["customs:read"])
    db.flush()
    again = identity_public.ensure_aduana_role(db)
    assert json.loads(again.permissions_json) == identity_public.ADUANA_PERMISSIONS

    names = {r.name for r in db.query(Role).all()}
    assert "aduana" in names
    assert "estoque" in names
