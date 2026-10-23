"""E0/E2: laboratory-only fixtures; projection invariants, not UI evidence."""
import json
import uuid
from decimal import Decimal
import pytest
from sqlalchemy import event
from app.catalog.models import Product
from app.inventory.models import StockBalance, StockLocation
from app.inventory.positions import positions
from app.reporting.commercial import availability
from app.identity.models import Role, User
from app.identity.security import hash_password


@pytest.mark.parametrize("count", [0, 1, 50, 51, 500, 501, 537])
def test_population_and_sort_do_not_change_totals(db, count):
    tag = uuid.uuid4().hex[:8]
    products = [Product(sku=f"UX-{tag}-{n:04}", description=f"Produto {tag} {n:04}", commercial_name=f"Produto {tag} {n:04}", unit="UN", ncm="12345678") for n in range(count)]
    db.add_all(products); db.flush()
    loc = db.query(StockLocation).filter_by(location_type="DOMESTIC").first()
    db.add_all([StockBalance(product_id=p.id, location_id=loc.id, qty=Decimal(n+1)) for n,p in enumerate(products)])
    db.flush()
    expected = str(count*(count+1)//2)
    a = availability(db,q=tag,limit=50,sort="commercial_name")
    b = availability(db,q=tag,limit=50,offset=50,sort="-available")
    assert a["total"] == b["total"] == count
    assert a["totals"] == b["totals"]
    assert a["by_regime"] == b["by_regime"] and a["by_category"] == b["by_category"]
    assert a["totals"]["units_available"] == expected
    calls = []
    def track(*args): calls.append(args[2])
    event.listen(db.bind,"before_cursor_execute",track)
    try: p = positions(db,q=tag,sort="-DOMESTIC",limit=25,offset=25)
    finally: event.remove(db.bind,"before_cursor_execute",track)
    assert len(calls) == 2, calls
    assert p["total"] == count and len(p["rows"]) == min(25,max(0,count-25))
    assert all(s.lstrip().upper().startswith("SELECT") for s in calls)
    if count: assert Decimal(p["totals"][0]["quantities"]["DOMESTIC"]) == Decimal(expected)


def test_units_and_positions_are_not_combined(db):
    tag=uuid.uuid4().hex[:8]
    products=[Product(sku=f"MIX-{tag}-{n}",description=tag,commercial_name=tag,unit=unit) for n,unit in enumerate(["UN","KG",None])]
    db.add_all(products);db.flush()
    locs={l.location_type:l for l in db.query(StockLocation).all()}
    db.add_all([StockBalance(product_id=p.id,location_id=locs[r].id,qty=Decimal(2)) for p,r in zip(products,["DOMESTIC","BONDED","QUARANTINE"])])
    db.flush()
    read=positions(db,q=tag)
    assert len(read["totals"])==3
    assert next(t for t in read["totals"] if t["unit"] is None)["quantities"]["QUARANTINE"] is None
    assert positions(db,q=tag,regime="BONDED")["total"]==1
    assert positions(db,q=tag,location_id=locs["DOMESTIC"].id)["total"]==1
    assert availability(db,q=tag)["totals"]["units_available"] is None
    unknown=availability(db,q=products[2].sku)
    assert unknown["totals"]["units_available"] is None
    assert all(r["qty"] is None for r in unknown["by_regime"])
    assert len(read["locations"]) >= 3


@pytest.mark.parametrize("permissions,status",[(["inventory:read"],200),(["reporting:read"],403),(["costing:read"],403),([],403)])
def test_stock_acl_does_not_require_reporting_or_costing(client,db,permissions,status):
    tag=uuid.uuid4().hex[:8]
    role=Role(name=f"ux-{tag}",permissions_json=json.dumps(permissions));db.add(role);db.flush()
    user=User(email=f"{tag}@example.com",name="Laboratório",password_hash=hash_password("lab-only"),role_id=role.id,is_active=True)
    db.add(user);db.commit()
    assert client.post("/api/auth/login",json={"email":user.email,"password":"lab-only"}).status_code==200
    assert client.get("/api/reporting/stock-positions").status_code==status
    assert client.get("/api/costing/products/1/sources").status_code==(200 if "costing:read" in permissions else 403)


def test_paging_validation_and_missing_product(admin_client):
    for query in ["limit=0","limit=101","offset=-1","product_id=0","regime=TRANSIT","sort=cost"]:
        assert admin_client.get("/api/reporting/stock-positions?"+query).status_code==422
    assert admin_client.get("/api/reporting/stock-positions?product_id=99999999").json()["total"]==0
    assert admin_client.get("/api/costing/products/99999999/sources").json()["total"]==0
    assert admin_client.get("/api/costing/products/99999999/versions/99999999").status_code==404
