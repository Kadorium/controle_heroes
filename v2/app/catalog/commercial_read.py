"""Read-only commercial descriptors. Classification uses persisted fields, never names."""
from hashlib import sha256
from sqlalchemy.orm import joinedload
from app.catalog.models import Product

SPORTS = {"BEACH TENNIS": "bt", "PADEL": "padel", "PICKLEBALL": "pickleball"}
MODALITIES = {"bt": "Beach Tennis", "padel": "Padel", "pickleball": "Pickleball", "unclassified": "Sem modalidade"}

def commercial_population(db):
    rows = db.query(Product).options(joinedload(Product.product_type), joinedload(Product.category)).all()
    result = []
    for p in rows:
        a = p.attributes or {}
        sport = str(a.get("sport") or "").upper().strip()
        parts = [s.strip() for s in sport.split("/")]
        sports = sorted({SPORTS[s] for s in parts if s in SPORTS}) if all(s in SPORTS for s in parts) else ["unclassified"]
        typ = p.product_type
        kind = f"type:{typ.id}" if typ else "unclassified"
        label = {"vestuario": "Roupas", "raquete": "Raquetes"}.get(typ.slug, typ.name) if typ else "Sem classificação"
        if typ and typ.slug == "consumivel" and a.get("consumable_kind") in ("BALL", "OVERGRIP"):
            kind += ":" + a["consumable_kind"]
            label = "Bolas" if a["consumable_kind"] == "BALL" else "Overgrips"
        model = str(a.get("model") or a.get("line") or "").strip()
        model_key = "model:"+sha256(f"{kind}|{model}|{a.get('collection_year','')}".encode()).hexdigest()[:24] if model else "unclassified"
        result.append({"product_id":p.id,"sku":p.sku,"name":p.commercial_name or p.description,
            "unit":p.unit,"modality_ids":sports,"modality_label":" + ".join(MODALITIES[s] for s in sports),
            "item_kind_id":kind,"item_kind_label":label,"model_id":model_key,"model_label":model or "Sem modelo",
            "category_id":str(p.category_id) if p.category_id else "unclassified", "size":p.size,"color":p.color,
            "pack_qty":a.get("pack_qty"),"active":p.is_active})
    return result
