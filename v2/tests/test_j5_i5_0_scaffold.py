"""I5-0 scaffold gates (updated after I5-4 public surface)."""

from __future__ import annotations

from app.customs import public as customs_public
from app.foundation.module_graph import ALLOWED_DEPS, MODULE_PACKAGES
from app.identity.public import ADMIN_PERMISSIONS, COMPRADOR_PERMISSIONS
from app.inventory import public as inventory_public


def test_module_packages_include_customs_inventory():
    assert "customs" in MODULE_PACKAGES
    assert "inventory" in MODULE_PACKAGES


def test_allowed_deps_customs_inventory_boundaries():
    assert ALLOWED_DEPS["customs"] == frozenset(
        {"billing", "logistics", "documents", "audit", "catalog"}
    )
    assert "treasury" not in ALLOWED_DEPS["customs"]
    assert ALLOWED_DEPS["inventory"] == frozenset(
        {"customs", "catalog", "logistics", "documents", "audit"}
    )
    assert "orders" not in ALLOWED_DEPS["inventory"]


def test_customs_public_i5_4_surface():
    assert hasattr(customs_public, "create_import_process")
    assert hasattr(customs_public, "link_invoice")
    assert hasattr(customs_public, "submit_import_process")
    assert hasattr(customs_public, "create_doganale_version")
    assert hasattr(customs_public, "activate_doganale_version")
    assert hasattr(customs_public, "register_divergence")
    assert hasattr(customs_public, "attach_provenance")
    assert hasattr(customs_public, "create_payee")
    assert hasattr(customs_public, "create_funding_request")
    assert hasattr(customs_public, "confirm_funding_request")
    assert hasattr(customs_public, "replace_value_bases")
    assert hasattr(customs_public, "structured_total")
    assert hasattr(customs_public, "funding_divergence")
    assert hasattr(customs_public, "nationalize")
    assert hasattr(customs_public, "create_nationalization")
    assert hasattr(customs_public, "confirm_nationalization")
    assert hasattr(customs_public, "reverse_nationalization")


def test_inventory_public_i5_4_implemented():
    assert hasattr(inventory_public, "get_sku_position")
    assert hasattr(inventory_public, "record_receipt")
    assert hasattr(inventory_public, "record_adjustment")
    assert hasattr(inventory_public, "list_movements")
    assert hasattr(inventory_public, "stock_balance")
    assert hasattr(inventory_public, "rebuild_stock_balances")
    assert callable(inventory_public.get_sku_position)


def test_admin_rbac_includes_customs_inventory():
    for perm in (
        "customs:read",
        "customs:write",
        "customs:clear",
        "customs:override",
        "inventory:read",
        "inventory:write",
        "inventory:adjust",
    ):
        assert perm in ADMIN_PERMISSIONS


def test_comprador_rbac_read_only_customs_inventory():
    assert "customs:read" in COMPRADOR_PERMISSIONS
    assert "inventory:read" in COMPRADOR_PERMISSIONS
    assert "customs:write" not in COMPRADOR_PERMISSIONS


def test_aduana_estoque_permission_lists_exported():
    from app.identity.public import ADUANA_PERMISSIONS, ESTOQUE_PERMISSIONS

    assert "customs:clear" in ADUANA_PERMISSIONS
    assert "inventory:adjust" in ESTOQUE_PERMISSIONS
