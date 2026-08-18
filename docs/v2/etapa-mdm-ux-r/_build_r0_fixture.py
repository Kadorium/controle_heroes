"""R0 forensic copies + visual fixture. Does not mutate product code or databases."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ASIS = ROOT / "docs/v2/etapa-mdm-ux-r/as-is"
PAGES = ASIS / "pages"
MIXED = ASIS / "mixed"
PROTO = ROOT / "docs/v2/etapa-mdm-ux-r/prototype"
FIX = PROTO / "fixtures"
SHOTS = PROTO / "screenshots"


def copy_forensic() -> None:
    for d in (PAGES, MIXED, FIX, SHOTS):
        d.mkdir(parents=True, exist_ok=True)
    pages = [
        "v2/frontend/src/features/catalog/ProductListPage.tsx",
        "v2/frontend/src/features/catalog/ProductDetailPage.tsx",
        "v2/frontend/src/features/catalog/ProductCreatePage.tsx",
        "v2/frontend/src/features/catalog/SupplierListPage.tsx",
        "v2/frontend/src/features/catalog/SupplierDetailPage.tsx",
        "v2/frontend/src/features/catalog/SupplierCreatePage.tsx",
        "v2/frontend/src/features/catalog/CatalogPages.test.tsx",
        "v2/frontend/src/features/admin/UsersListPage.tsx",
        "v2/frontend/src/features/admin/UserDetailPage.tsx",
        "v2/frontend/src/features/admin/UserCreatePage.tsx",
        "v2/frontend/src/features/admin/UsersPages.test.tsx",
    ]
    mixed = [
        "v2/frontend/src/app-shell/AppShell.tsx",
        "v2/frontend/src/app-shell/AppShell.nav.test.tsx",
        "v2/frontend/src/App.tsx",
    ]
    for rel in pages:
        shutil.copy2(ROOT / rel, PAGES / Path(rel).name)
    for rel in mixed:
        shutil.copy2(ROOT / rel, MIXED / Path(rel).name)

    st = subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True, encoding="utf-8")
    (ASIS / "git-status-short.txt").write_text(st, encoding="utf-8")
    head = subprocess.check_output(
        ["git", "log", "-1", "--format=%H %s"], cwd=ROOT, text=True, encoding="utf-8"
    ).strip()
    (ASIS / "git-head.txt").write_text(head + "\n", encoding="utf-8")
    lines = [line for line in st.splitlines() if line.strip()]
    untracked = [line for line in lines if line.startswith("??")]
    (ASIS / "git-counts.txt").write_text(
        f"status_lines={len(lines)}\nuntracked={len(untracked)}\nhead={head}\n",
        encoding="utf-8",
    )


def origin_iso(pais: str | None) -> str | None:
    value = (pais or "").strip().upper()
    if value in {"ITALIA", "ITÁLIA", "ITALY", "IT"}:
        return "IT"
    if value in {"BRASIL", "BRAZIL", "BR"}:
        return "BR"
    return None


def ean_from(sku: str, index: int) -> str:
    digest = hashlib.sha1(f"{sku}:{index}".encode()).hexdigest()
    digits = "".join(ch for ch in digest if ch.isdigit())[:12].ljust(12, "0")
    checksum = sum(int(d) * (3 if k % 2 else 1) for k, d in enumerate(digits))
    check = (10 - (checksum % 10)) % 10
    return digits + str(check)


def is_incomplete(product: dict) -> bool:
    return not product.get("ncm") or not product.get("ean") or product.get("quality_unknown")


def build_fixture() -> dict:
    csv_path = ROOT / "v1/heroes_produtos_epic_import_final.csv"
    sizes = ["L", "M", "One"]
    colors = ["Black", "White", "Red", "Blue"]
    ncm_racket = "95065900"
    ncm_bag = "42029200"
    products: list[dict] = []
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    for i, row in enumerate(rows, start=1):
        sku = (row.get("sku_sugerido") or "").strip()
        desc = (row.get("descricao_comercial_curta") or row.get("nome_produto") or "").strip()
        status = (row.get("status_produto") or "").strip().upper()
        tipo = (row.get("tipo_produto") or "").upper()
        ncm_raw = (row.get("ncm") or "").strip()
        ncm = re.sub(r"\D", "", ncm_raw) or None
        if ncm and len(ncm) != 8:
            ncm = None
        peso = row.get("peso_kg") or ""
        try:
            weight = float(str(peso).replace(",", ".")) if str(peso).strip() else None
        except ValueError:
            weight = None
        unit = (row.get("unidade_medida") or "").strip() or None
        orig = origin_iso(row.get("pais_origem"))
        is_active = status != "DISCONTINUED"
        unknown = status == "UNKNOWN"
        size = color = ean = None
        enrich: list[str] = []
        generic_csv = desc.lower().startswith("produto heroes")
        rich_candidate = is_active and not unknown and not generic_csv
        if rich_candidate and i % 2 == 1:
            ean = ean_from(sku, i)
            enrich.append("ean")
        if rich_candidate and i % 2 == 0 and not ncm:
            ncm = ncm_racket if "RAQUETE" in tipo else ncm_bag
            enrich.append("ncm")
        if rich_candidate and i % 3 == 0 and not ncm:
            ncm = ncm_racket if "RAQUETE" in tipo else ncm_bag
            enrich.append("ncm")
        if "RAQUETE" in tipo and (i % 2 == 0 or rich_candidate):
            size = sizes[i % 2]
            enrich.append("size")
        nome = row.get("nome_produto") or ""
        if re.search(r"WHITE|BRANCO", nome, re.I):
            color = "White"
            enrich.append("color")
        elif re.search(r"VERDE|GREEN", nome, re.I):
            color = "Green"
            enrich.append("color")
        elif rich_candidate and i % 2 == 0:
            color = colors[i % len(colors)]
            enrich.append("color")
        elif is_active and i % 5 == 0:
            color = colors[i % len(colors)]
            enrich.append("color")
        if orig is None and (rich_candidate or (is_active and i % 2 == 0)):
            orig = "IT"
            enrich.append("origin")
        if unit is None:
            unit = "UN"
            enrich.append("unit")
        if weight is None and "RAQUETE" in tipo and (i % 3 == 0 or rich_candidate):
            weight = 0.325
            enrich.append("weight")
        products.append(
            {
                "id": i,
                "sku": sku,
                "description": desc,
                "ean": ean,
                "ncm": ncm,
                "size": size,
                "color": color,
                "country_of_origin": orig,
                "unit": unit,
                "net_weight_kg": weight,
                "is_active": is_active,
                "quality_unknown": unknown,
                "source": "csv-v1-visual",
                "enrichment": enrich,
                "grupo": (row.get("grupo") or "").strip() or None,
                "tipo": (row.get("tipo_produto") or "").strip() or None,
                "nome_produto": (row.get("nome_produto") or "").strip() or None,
            }
        )

    fake = [
        {
            "sku": "PROTO-B5-EQ-SKU",
            "description": "PROTO-B5-EQ-SKU",
            "ean": None,
            "ncm": None,
            "size": None,
            "color": None,
            "country_of_origin": None,
            "unit": None,
            "net_weight_kg": None,
            "is_active": True,
            "quality_unknown": False,
            "source": "proto-fake",
            "enrichment": ["b5-eq-sku"],
            "grupo": None,
            "tipo": None,
            "nome_produto": None,
        },
        {
            "sku": "PROTO-B5-GENERIC",
            "description": "Item proto walk",
            "ean": None,
            "ncm": None,
            "size": None,
            "color": None,
            "country_of_origin": None,
            "unit": None,
            "net_weight_kg": None,
            "is_active": True,
            "quality_unknown": False,
            "source": "proto-fake",
            "enrichment": ["b5-generic"],
            "grupo": None,
            "tipo": None,
            "nome_produto": None,
        },
        {
            "sku": "PROTO-B5-EMPTY",
            "description": "",
            "ean": None,
            "ncm": None,
            "size": None,
            "color": None,
            "country_of_origin": None,
            "unit": None,
            "net_weight_kg": None,
            "is_active": True,
            "quality_unknown": False,
            "source": "proto-fake",
            "enrichment": ["b5-empty"],
            "grupo": None,
            "tipo": None,
            "nome_produto": None,
        },
        {
            "sku": "PROTO-INCOMPLETE-BARE",
            "description": "Raquete sem dados fiscais",
            "ean": None,
            "ncm": None,
            "size": None,
            "color": None,
            "country_of_origin": None,
            "unit": "UN",
            "net_weight_kg": None,
            "is_active": True,
            "quality_unknown": False,
            "source": "proto-fake",
            "enrichment": ["incomplete"],
            "grupo": "RAQUETES",
            "tipo": "RAQUETE",
            "nome_produto": None,
        },
        {
            "sku": "8057628953814",
            "description": "WASH BAG STARLIGHT — RED",
            "ean": "8057628953814",
            "ncm": "42029200",
            "size": "Large",
            "color": "Red",
            "country_of_origin": "IT",
            "unit": "UN",
            "net_weight_kg": 0.42,
            "is_active": True,
            "quality_unknown": False,
            "source": "proto-fake",
            "enrichment": ["rich", "human-identity-target"],
            "grupo": "ACESSORIOS",
            "tipo": "BOLSA",
            "nome_produto": "WASH BAG STARLIGHT",
        },
        {
            "sku": "PROTO-INACTIVE-OLYMPIA",
            "description": "Travel Bag OLYMPIA 2024 (fora de linha)",
            "ean": "8057628000001",
            "ncm": "42029200",
            "size": None,
            "color": "Green",
            "country_of_origin": "IT",
            "unit": "UN",
            "net_weight_kg": 1.1,
            "is_active": False,
            "quality_unknown": False,
            "source": "proto-fake",
            "enrichment": ["inactive"],
            "grupo": "ACESSORIOS",
            "tipo": "BOLSA VIAGEM",
            "nome_produto": None,
        },
        {
            "sku": "PROTO-NCM-ONLY",
            "description": "Overgrip H Level sem EAN",
            "ean": None,
            "ncm": "40161010",
            "size": None,
            "color": "White",
            "country_of_origin": "IT",
            "unit": "PCT",
            "net_weight_kg": 0.18,
            "is_active": True,
            "quality_unknown": False,
            "source": "proto-fake",
            "enrichment": ["ncm-only"],
            "grupo": "ACESSORIOS",
            "tipo": "OVERGRIP",
            "nome_produto": None,
        },
        {
            "sku": "PROTO-EAN-ONLY",
            "description": "Headband FIERCE sem NCM",
            "ean": "8057628000002",
            "ncm": None,
            "size": "One",
            "color": "Black",
            "country_of_origin": "IT",
            "unit": "UN",
            "net_weight_kg": 0.04,
            "is_active": True,
            "quality_unknown": False,
            "source": "proto-fake",
            "enrichment": ["ean-only"],
            "grupo": "ACESSORIOS",
            "tipo": "ACESSORIO",
            "nome_produto": None,
        },
    ]
    base_id = len(products)
    for j, item in enumerate(fake, start=1):
        row = dict(item)
        row["id"] = base_id + j
        products.append(row)

    stats = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "csv_rows": len(rows),
        "fake_rows": len(fake),
        "total": len(products),
        "active": sum(1 for product in products if product["is_active"]),
        "inactive": sum(1 for product in products if not product["is_active"]),
        "incomplete": sum(1 for product in products if is_incomplete(product)),
        "missing_ncm": sum(1 for product in products if not product.get("ncm")),
        "with_size": sum(1 for product in products if product.get("size")),
        "with_color": sum(1 for product in products if product.get("color")),
        "with_ean": sum(1 for product in products if product.get("ean")),
        "note": (
            "CSV V1 is a static visual fixture only. Not a V1->V2 migration. "
            "Fake rows are labeled source=proto-fake."
        ),
    }
    return {
        "meta": stats,
        "products": products,
        "supplier": {
            "id": 26,
            "name": "Heroe's Srl",
            "code": "HEROES",
            "country_code": "IT",
            "tax_id": None,
            "is_active": True,
            "orders": 6,
        },
        "users": [
            {
                "id": 1,
                "name": "Administrador",
                "email": "admin@epic.com.br",
                "role": "admin",
                "is_active": True,
            },
            {
                "id": 2,
                "name": "Ana Operações",
                "email": "ana.ops@epic.com.br",
                "role": "operator",
                "is_active": True,
            },
            {
                "id": 3,
                "name": "Bruno Leitura",
                "email": "bruno.leitura@epic.com.br",
                "role": "viewer",
                "is_active": True,
            },
            {
                "id": 4,
                "name": "Carla Inativa",
                "email": "carla.inativa@epic.com.br",
                "role": "operator",
                "is_active": False,
            },
        ],
        "logistics_provider": {"id": 1, "name": "DHL Global Forwarding", "is_active": True},
    }


def main() -> None:
    copy_forensic()
    payload = build_fixture()
    (FIX / "catalog-visual.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("R0 copies ok")
    print("fixture", payload["meta"])


if __name__ == "__main__":
    main()
