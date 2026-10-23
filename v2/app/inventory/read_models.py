from typing import Literal
from pydantic import BaseModel

class Quantities(BaseModel):
    DOMESTIC: str
    BONDED: str
    QUARANTINE: str

class TotalQuantities(BaseModel):
    DOMESTIC: str | None
    BONDED: str | None
    QUARANTINE: str | None

class PositionBalance(BaseModel):
    location_id: int
    code: str
    name: str
    regime: Literal["DOMESTIC", "BONDED", "QUARANTINE"]
    qty: str

class ProductPosition(BaseModel):
    product_id: int
    sku: str
    name: str
    unit: str | None
    quantities: Quantities
    balances: list[PositionBalance]

class UnitPositionTotal(BaseModel):
    unit: str | None
    quantities: TotalQuantities
    sku_count: int
    quantity_state: Literal["known", "unit_missing"]

class PositionLocation(BaseModel):
    id: int
    name: str
    regime: Literal["DOMESTIC", "BONDED", "QUARANTINE"]

class StockPositionsResponse(BaseModel):
    locations: list[PositionLocation]
    rows: list[ProductPosition]
    total: int
    limit: int
    offset: int
    totals: list[UnitPositionTotal]
    filters: dict[str, str | int | None]
    scope: str
    state: Literal["ok", "empty"]
    generated_at: str
