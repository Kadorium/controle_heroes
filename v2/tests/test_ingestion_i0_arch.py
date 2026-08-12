"""J3-I0/I3/I4/I5 architecture guards."""

from app.foundation.module_graph import ALLOWED_DEPS


def test_ingestion_deps_i3():
    """J3-I3: ingestion depende de audit + documents + orders + catalog (commit path).
    J3-I4: billing adicionado (create_invoice + set_terms via billing.public).
    J3-I5: logistics + customs adicionados (PL Detail commit / Doganale commit).

    Dependências proibidas: treasury, inventory.
    """
    allowed = ALLOWED_DEPS["ingestion"]
    # I3 additions
    assert "audit" in allowed
    assert "documents" in allowed
    assert "orders" in allowed
    assert "catalog" in allowed
    # I4 addition: billing authorised for Invoice DRAFT creation
    assert "billing" in allowed
    # I5 additions
    assert "logistics" in allowed
    assert "customs" in allowed
    # Never allowed in ingestion
    for forbidden in ("treasury", "inventory"):
        assert forbidden not in allowed, f"{forbidden} must not be in ingestion deps"


def test_ingestion_deps_i4_billing():
    """J3-I4: billing must be in ingestion deps (create_invoice path)."""
    assert "billing" in ALLOWED_DEPS["ingestion"]
