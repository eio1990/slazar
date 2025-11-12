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
    source_operation_type: Optional[str] = None
    source_operation_id: Optional[str] = None
    parent_movement_id: Optional[int] = None
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

class BatchOperationItem(BaseModel):
    nomenclature_id: int
    quantity: float
    price_per_unit: Optional[float] = None
    metadata: Optional[dict] = None

class BatchStockOperation(BaseModel):
    operations: List[BatchOperationItem]
    source_operation_type: Optional[str] = None
    source_operation_id: Optional[str] = None
    idempotency_key: str
    all_or_nothing: bool = True

class BatchOperationResult(BaseModel):
    nomenclature_id: int
    status: str  # 'success' or 'error'
    message: str
    balance_after: Optional[float] = None

class BatchResponse(BaseModel):
    status: str  # 'success', 'partial_success', or 'error'
    total_operations: int
    successful: int
    failed: int
    results: List[BatchOperationResult]
    message: str


# Production Module Models

class RecipeStep(BaseModel):
    id: int
    step_order: int
    step_type: str
    step_name: str
    duration_days: float
    parameters: Optional[dict] = None
    description: Optional[str] = None

class Recipe(BaseModel):
    id: int
    name: str
    target_product_id: int
    target_product_name: Optional[str] = None
    expected_yield_min: float
    expected_yield_max: float
    description: Optional[str] = None
    steps: List[RecipeStep] = []

class BatchCreate(BaseModel):
    recipe_id: int
    initial_weight: float
    trim_waste: Optional[float] = 0
    trim_returned: bool = False
    operator_notes: Optional[str] = None

class BatchOperationCreate(BaseModel):
    step_id: int
    weight_before: Optional[float] = None
    weight_after: Optional[float] = None
    parameters: Optional[dict] = None
    notes: Optional[str] = None
    idempotency_key: str

class BatchMixProduction(BaseModel):
    mix_nomenclature_id: int
    produced_quantity: float
    used_quantity: float
    leftover_quantity: float
    warehouse_mix_used: float
    idempotency_key: str

class Batch(BaseModel):
    id: int
    batch_number: str
    recipe_id: int
    recipe_name: Optional[str] = None
    status: str
    current_step: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    initial_weight: float
    final_weight: Optional[float] = None
    trim_waste: Optional[float] = None
    trim_returned: Optional[bool] = None
    operator_notes: Optional[str] = None

class BatchComplete(BaseModel):
    final_weight: float
    notes: Optional[str] = None
    idempotency_key: str

class BatchSalting(BaseModel):
    salt_quantity: float
    water_quantity: float
    notes: Optional[str] = None
    idempotency_key: str
