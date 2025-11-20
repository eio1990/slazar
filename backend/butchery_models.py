from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# Recipe models
class ButcheryRecipeOutput(BaseModel):
    output_nomenclature_id: int
    output_name: str
    yield_percentage: float
    is_main_output: bool
    output_type: str  # 'main', 'by-product', 'waste'

class ButcheryRecipe(BaseModel):
    id: int
    name: str
    source_nomenclature_id: int
    source_name: str
    description: Optional[str] = None
    level: int
    is_active: bool
    outputs: List[ButcheryRecipeOutput]

# Operation models
class ButcheryOperationCreate(BaseModel):
    recipe_id: int
    source_nomenclature_id: int
    input_weight: float
    notes: Optional[str] = None
    idempotency_key: str

class ButcheryOutputInput(BaseModel):
    output_nomenclature_id: int
    actual_weight: float
    notes: Optional[str] = None

class ButcheryOperationComplete(BaseModel):
    outputs: List[ButcheryOutputInput]
    notes: Optional[str] = None
    operator_notes: Optional[str] = None  # Alias for notes
    idempotency_key: Optional[str] = None  # Made optional

class ButcheryOperation(BaseModel):
    id: int
    operation_number: str
    recipe_id: int
    recipe_name: str
    source_nomenclature_id: int
    source_name: str
    input_weight: float
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    operator_notes: Optional[str] = None

class ButcheryOperationOutput(BaseModel):
    output_nomenclature_id: int
    output_name: str
    expected_weight: Optional[float] = None
    actual_weight: float
    yield_percentage: Optional[float] = None
