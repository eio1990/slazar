from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime
from decimal import Decimal

class NomenclatureBase(BaseModel):
    name: str
    category: str
    unit: str
    precision_digits: int = 2

class NomenclatureCreate(NomenclatureBase):
    pass

class Nomenclature(NomenclatureBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class StockOperation(BaseModel):
    nomenclature_id: int
    quantity: float
    price_per_unit: Optional[float] = None
    idempotency_key: str
    metadata: Optional[dict] = None

class StockMovement(BaseModel):
    id: int
    nomenclature_id: int
    operation_type: str
    quantity: float
    balance_after: float
    price_per_unit: Optional[float] = None
    idempotency_key: str
    metadata: Optional[str] = None
    operation_date: datetime
    created_at: datetime

class StockBalance(BaseModel):
    nomenclature_id: int
    nomenclature_name: str
    category: str
    unit: str
    quantity: float
    last_updated: datetime

class InventorySessionCreate(BaseModel):
    session_type: Literal["full", "partial"]
    idempotency_key: str
    metadata: Optional[dict] = None

class InventoryItemCreate(BaseModel):
    nomenclature_id: int
    actual_quantity: float

class InventorySession(BaseModel):
    id: int
    session_type: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    idempotency_key: str
    metadata: Optional[str] = None

class InventoryComplete(BaseModel):
    session_id: int
    items: List[InventoryItemCreate]
    idempotency_key: str

class SyncOperation(BaseModel):
    operation_type: Literal["receipt", "withdrawal", "inventory"]
    data: dict
    idempotency_key: str
    timestamp: datetime

class SyncBatch(BaseModel):
    operations: List[SyncOperation]
