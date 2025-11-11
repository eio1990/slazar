"""
Production module API endpoints
"""
from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime
import json

from database import get_db_connection
from models import Recipe, RecipeStep, BatchCreate, Batch, BatchComplete, BatchOperationCreate, BatchMixProduction

router = APIRouter(prefix="/api/production", tags=["production"])

# Constants
FENUGREEK_ID = 19  # Пажитник in nomenclature
WATER_ID = 71      # Вода in nomenclature
FENUGREEK_WATER_RATIO = 4  # 1:4 rule

def calculate_produced_mix(spices: list) -> float:
    """
    Calculate produced mix quantity with fenugreek water rule
    ProducedMix = Σ(all spices except fenugreek) + (fenugreek_weight × 4)
    """
    total = 0
    fenugreek_weight = 0
    
    for spice in spices:
        nomenclature_id = spice.get('nomenclature_id')
        quantity = spice.get('quantity', 0)
        
        if nomenclature_id == FENUGREEK_ID:
            fenugreek_weight = quantity
        elif nomenclature_id != WATER_ID:  # Don't count manually added water
            total += quantity
    
    # Add fenugreek and its required water (1:4 ratio)
    if fenugreek_weight > 0:
        total += fenugreek_weight + (fenugreek_weight * FENUGREEK_WATER_RATIO)
    
    return total



@router.get("/recipes", response_model=List[Recipe])
async def get_recipes():
    """Get all recipes"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.id, r.name, r.target_product_id, n.name as product_name,
                   r.expected_yield_min, r.expected_yield_max, r.description
            FROM recipes r
            LEFT JOIN nomenclature n ON r.target_product_id = n.id
            ORDER BY r.name
        """)
        
        recipes = []
        for row in cursor.fetchall():
            recipes.append(Recipe(
                id=row.id,
                name=row.name,
                target_product_id=row.target_product_id,
                target_product_name=row.product_name,
                expected_yield_min=float(row.expected_yield_min),
                expected_yield_max=float(row.expected_yield_max),
                description=row.description,
                steps=[]
            ))
        
        return recipes

@router.get("/recipes/{recipe_id}", response_model=Recipe)
async def get_recipe(recipe_id: int):
    """Get recipe with steps"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get recipe
        cursor.execute("""
            SELECT r.id, r.name, r.target_product_id, n.name as product_name,
                   r.expected_yield_min, r.expected_yield_max, r.description
            FROM recipes r
            LEFT JOIN nomenclature n ON r.target_product_id = n.id
            WHERE r.id = ?
        """, recipe_id)
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Recipe not found")
        
        recipe = Recipe(
            id=row.id,
            name=row.name,
            target_product_id=row.target_product_id,
            target_product_name=row.product_name,
            expected_yield_min=float(row.expected_yield_min),
            expected_yield_max=float(row.expected_yield_max),
            description=row.description,
            steps=[]
        )
        
        # Get steps
        cursor.execute("""
            SELECT id, step_order, step_type, step_name, duration_days, parameters, description
            FROM recipe_steps
            WHERE recipe_id = ?
            ORDER BY step_order
        """, recipe_id)
        
        for step_row in cursor.fetchall():
            params = None
            if step_row.parameters:
                try:
                    params = json.loads(step_row.parameters)
                except:
                    params = None
            
            recipe.steps.append(RecipeStep(
                id=step_row.id,
                step_order=step_row.step_order,
                step_type=step_row.step_type,
                step_name=step_row.step_name,
                duration_days=float(step_row.duration_days),
                parameters=params,
                description=step_row.description
            ))
        
        return recipe

@router.get("/recipes/{recipe_id}/spices")
async def get_recipe_spices(recipe_id: int):
    """Get spices/ingredients for a recipe"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get spices
        cursor.execute("""
            SELECT rs.id, rs.nomenclature_id, n.name, rs.quantity_per_100kg, rs.is_fenugreek
            FROM recipe_spices rs
            JOIN nomenclature n ON rs.nomenclature_id = n.id
            WHERE rs.recipe_id = ?
            ORDER BY n.name
        """, recipe_id)
        
        spices = []
        for row in cursor.fetchall():
            spices.append({
                'id': row.id,
                'nomenclature_id': row.nomenclature_id,
                'name': row.name,
                'quantity_per_100kg': float(row.quantity_per_100kg) if row.quantity_per_100kg else 0,
                'is_fenugreek': bool(row.is_fenugreek)
            })
        
        # Get ingredients
        cursor.execute("""
            SELECT ri.id, ri.nomenclature_id, n.name, ri.quantity_per_100kg, ri.is_optional
            FROM recipe_ingredients ri
            JOIN nomenclature n ON ri.nomenclature_id = n.id
            WHERE ri.recipe_id = ?
            ORDER BY n.name
        """, recipe_id)
        
        ingredients = []
        for row in cursor.fetchall():
            ingredients.append({
                'id': row.id,
                'nomenclature_id': row.nomenclature_id,
                'name': row.name,
                'quantity_per_100kg': float(row.quantity_per_100kg) if row.quantity_per_100kg else 0,
                'is_optional': bool(row.is_optional)
            })
        
        return {
            'spices': spices,
            'ingredients': ingredients
        }

@router.post("/batches", response_model=Batch)
async def create_batch(batch_data: BatchCreate):
    """Create new production batch with stock availability check"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Verify recipe exists and get target product
        cursor.execute("""
            SELECT r.name, r.target_product_id, n.name as product_name
            FROM recipes r
            JOIN nomenclature n ON r.target_product_id = n.id
            WHERE r.id = ?
        """, batch_data.recipe_id)
        recipe = cursor.fetchone()
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")
        
        # Check raw material availability on stock
        # Get main ingredient from recipe
        cursor.execute("""
            SELECT ri.nomenclature_id, n.name, ri.quantity_per_100kg
            FROM recipe_ingredients ri
            JOIN nomenclature n ON ri.nomenclature_id = n.id
            WHERE ri.recipe_id = ? AND ri.is_optional = 0
            ORDER BY ri.quantity_per_100kg DESC
        """, batch_data.recipe_id)
        
        main_ingredient = cursor.fetchone()
        if main_ingredient:
            ingredient_id = main_ingredient.nomenclature_id
            ingredient_name = main_ingredient.name
            
            # Check stock balance
            cursor.execute("""
                SELECT COALESCE(quantity, 0) as quantity
                FROM stock_balances
                WHERE nomenclature_id = ?
            """, ingredient_id)
            
            balance_row = cursor.fetchone()
            current_balance = float(balance_row[0]) if balance_row else 0.0
            
            # Check if enough stock (considering trim waste)
            total_required = batch_data.initial_weight
            if batch_data.trim_waste and batch_data.trim_waste > 0:
                total_required += batch_data.trim_waste
            
            if current_balance < total_required:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient stock for {ingredient_name}. "
                           f"Available: {current_balance:.2f} kg, Required: {total_required:.2f} kg"
                )
        
        # Generate batch number
        today = datetime.now().strftime("%d%m%Y")
        cursor.execute("""
            SELECT COUNT(*) FROM batches 
            WHERE batch_number LIKE ?
        """, f"BATCH-{today}%")
        count = cursor.fetchone()[0] + 1
        batch_number = f"BATCH-{today}-{count:03d}"
        
        # Create batch
        cursor.execute("""
            INSERT INTO batches (
                batch_number, recipe_id, status, current_step,
                initial_weight, trim_waste, trim_returned, operator_notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, batch_number, batch_data.recipe_id, 'created', 0,
            batch_data.initial_weight, batch_data.trim_waste,
            batch_data.trim_returned, batch_data.operator_notes)
        
        batch_id = cursor.execute("SELECT @@IDENTITY").fetchone()[0]
        
        # Automatically consume raw materials (списання сировини)
        if main_ingredient:
            ingredient_id = main_ingredient.nomenclature_id
            quantity_to_consume = batch_data.initial_weight
            
            # Add trim waste if not returned to stock
            if batch_data.trim_waste and batch_data.trim_waste > 0 and not batch_data.trim_returned:
                quantity_to_consume += batch_data.trim_waste
            
            # Create idempotency key for material consumption
            material_key = f"batch-{batch_id}-raw-material-{datetime.now().timestamp()}"
            
            # Create withdrawal movement
            new_balance = current_balance - quantity_to_consume
            cursor.execute("""
                INSERT INTO stock_movements (
                    nomenclature_id, operation_type, quantity, balance_after,
                    source_operation_type, source_operation_id,
                    idempotency_key, operation_date, metadata
                )
                VALUES (?, 'withdrawal', ?, ?, 'production', ?, ?, GETUTCDATE(), ?)
            """, ingredient_id, quantity_to_consume, new_balance,
                batch_number, material_key,
                json.dumps({
                    'batch_id': batch_id,
                    'batch_number': batch_number,
                    'material_type': 'raw_material',
                    'auto_consumed': True
                }))
            
            # Update stock balance
            cursor.execute("""
                UPDATE stock_balances
                SET quantity = ?,
                    last_updated = GETUTCDATE()
                WHERE nomenclature_id = ?
            """, new_balance, ingredient_id)
            
            # Record in batch_materials
            cursor.execute("""
                INSERT INTO batch_materials (
                    batch_id, nomenclature_id, material_type, quantity_used, notes
                )
                VALUES (?, ?, 'raw_material', ?, 'Auto-consumed at batch start')
            """, batch_id, ingredient_id, quantity_to_consume)
        
        # Get created batch
        cursor.execute("""
            SELECT b.id, b.batch_number, b.recipe_id, r.name as recipe_name,
                   b.status, b.current_step, b.started_at, b.completed_at,
                   b.initial_weight, b.final_weight, b.trim_waste,
                   b.trim_returned, b.operator_notes
            FROM batches b
            LEFT JOIN recipes r ON b.recipe_id = r.id
            WHERE b.id = ?
        """, batch_id)
        
        row = cursor.fetchone()
        conn.commit()
        
        return Batch(
            id=row.id,
            batch_number=row.batch_number,
            recipe_id=row.recipe_id,
            recipe_name=row.recipe_name,
            status=row.status,
            current_step=row.current_step,
            started_at=row.started_at,
            completed_at=row.completed_at,
            initial_weight=float(row.initial_weight),
            final_weight=float(row.final_weight) if row.final_weight else None,
            trim_waste=float(row.trim_waste) if row.trim_waste else None,
            trim_returned=row.trim_returned,
            operator_notes=row.operator_notes
        )

@router.get("/batches", response_model=List[Batch])
async def get_batches(status: str = None):
    """Get all batches with optional status filter"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        query = """
            SELECT b.id, b.batch_number, b.recipe_id, r.name as recipe_name,
                   b.status, b.current_step, b.started_at, b.completed_at,
                   b.initial_weight, b.final_weight, b.trim_waste,
                   b.trim_returned, b.operator_notes
            FROM batches b
            LEFT JOIN recipes r ON b.recipe_id = r.id
        """
        
        if status:
            query += " WHERE b.status = ?"
            cursor.execute(query + " ORDER BY b.started_at DESC", status)
        else:
            cursor.execute(query + " ORDER BY b.started_at DESC")
        
        batches = []
        for row in cursor.fetchall():
            batches.append(Batch(
                id=row.id,
                batch_number=row.batch_number,
                recipe_id=row.recipe_id,
                recipe_name=row.recipe_name,
                status=row.status,
                current_step=row.current_step,
                started_at=row.started_at,
                completed_at=row.completed_at,
                initial_weight=float(row.initial_weight),
                final_weight=float(row.final_weight) if row.final_weight else None,
                trim_waste=float(row.trim_waste) if row.trim_waste else None,
                trim_returned=row.trim_returned,
                operator_notes=row.operator_notes
            ))
        
        return batches

@router.get("/batches/{batch_id}", response_model=Batch)
async def get_batch(batch_id: int):
    """Get batch details"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT b.id, b.batch_number, b.recipe_id, r.name as recipe_name,
                   b.status, b.current_step, b.started_at, b.completed_at,
                   b.initial_weight, b.final_weight, b.trim_waste,
                   b.trim_returned, b.operator_notes
            FROM batches b
            LEFT JOIN recipes r ON b.recipe_id = r.id
            WHERE b.id = ?
        """, batch_id)
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        return Batch(
            id=row.id,
            batch_number=row.batch_number,
            recipe_id=row.recipe_id,
            recipe_name=row.recipe_name,
            status=row.status,
            current_step=row.current_step,
            started_at=row.started_at,
            completed_at=row.completed_at,
            initial_weight=float(row.initial_weight),
            final_weight=float(row.final_weight) if row.final_weight else None,
            trim_waste=float(row.trim_waste) if row.trim_waste else None,
            trim_returned=row.trim_returned,
            operator_notes=row.operator_notes
        )


@router.post("/batches/{batch_id}/operations")
async def add_batch_operation(batch_id: int, operation: BatchOperationCreate):
    """Add an operation to a batch (step completion)"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get batch and current step
        cursor.execute("""
            SELECT b.*, rs.step_order, rs.step_type, rs.step_name
            FROM batches b
            LEFT JOIN recipe_steps rs ON b.recipe_id = rs.recipe_id AND rs.id = ?
            WHERE b.id = ?
        """, operation.step_id, batch_id)
        
        batch = cursor.fetchone()
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        if batch.status == 'completed':
            raise HTTPException(status_code=400, detail="Batch already completed")
        
        # Check idempotency
        cursor.execute(
            "SELECT id FROM batch_operations WHERE idempotency_key = ?",
            operation.idempotency_key
        )
        if cursor.fetchone():
            return {"message": "Operation already recorded", "batch_id": batch_id}
        
        # Insert operation
        cursor.execute("""
            INSERT INTO batch_operations (
                batch_id, step_id, operation_type, status,
                weight_before, weight_after, parameters, notes, idempotency_key
            )
            VALUES (?, ?, ?, 'completed', ?, ?, ?, ?, ?)
        """, batch_id, operation.step_id, batch.step_type,
            operation.weight_before, operation.weight_after,
            json.dumps(operation.parameters) if operation.parameters else None,
            operation.notes, operation.idempotency_key)
        
        # Update batch status and current step
        new_status = 'in_progress' if batch.status == 'created' else batch.status
        cursor.execute("""
            UPDATE batches
            SET status = ?,
                current_step = ?,
                updated_at = GETUTCDATE()
            WHERE id = ?
        """, new_status, batch.step_order, batch_id)
        
        conn.commit()
        
        return {
            "message": "Operation added successfully",
            "batch_id": batch_id,
            "step_completed": batch.step_name,
            "current_step": batch.step_order
        }

@router.get("/batches/{batch_id}/operations")
async def get_batch_operations(batch_id: int):
    """Get all operations for a batch"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT bo.id, bo.batch_id, bo.step_id, bo.operation_type, bo.status,
                   bo.started_at, bo.completed_at, bo.weight_before, bo.weight_after,
                   bo.parameters, bo.notes, rs.step_name, rs.step_order
            FROM batch_operations bo
            JOIN recipe_steps rs ON bo.step_id = rs.id
            WHERE bo.batch_id = ?
            ORDER BY rs.step_order, bo.started_at
        """, batch_id)
        
        operations = []
        for row in cursor.fetchall():
            params = None
            if row.parameters:
                try:
                    params = json.loads(row.parameters)
                except:
                    params = None
            
            operations.append({
                'id': row.id,
                'batch_id': row.batch_id,
                'step_id': row.step_id,
                'operation_type': row.operation_type,
                'status': row.status,
                'started_at': row.started_at.isoformat() if row.started_at else None,
                'completed_at': row.completed_at.isoformat() if row.completed_at else None,
                'weight_before': float(row.weight_before) if row.weight_before else None,
                'weight_after': float(row.weight_after) if row.weight_after else None,
                'parameters': params,
                'notes': row.notes,
                'step_name': row.step_name,
                'step_order': row.step_order
            })
        
        return operations


@router.put("/batches/{batch_id}/complete")

@router.post("/batches/{batch_id}/mix")
async def produce_mix(batch_id: int, mix_data: BatchMixProduction):
    """Produce mix (Chaman/Marinade) with fenugreek water rule"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get batch
        cursor.execute("SELECT * FROM batches WHERE id = ?", batch_id)
        batch = cursor.fetchone()
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        if batch.status == 'completed':
            raise HTTPException(status_code=400, detail="Batch already completed")
        
        # Check idempotency
        cursor.execute(
            "SELECT id FROM batch_mix_production WHERE idempotency_key = ?",
            mix_data.idempotency_key
        )
        if cursor.fetchone():
            return {"message": "Mix already produced", "batch_id": batch_id}
        
        # Insert mix production record
        cursor.execute("""
            INSERT INTO batch_mix_production (
                batch_id, mix_nomenclature_id, produced_quantity, used_quantity,
                leftover_quantity, warehouse_mix_used, idempotency_key
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, batch_id, mix_data.mix_nomenclature_id, mix_data.produced_quantity,
            mix_data.used_quantity, mix_data.leftover_quantity,
            mix_data.warehouse_mix_used, mix_data.idempotency_key)
        
        # If leftover > 0, create stock receipt for mix
        if mix_data.leftover_quantity > 0:
            leftover_key = f"mix-leftover-{batch_id}-{mix_data.idempotency_key}"
            
            cursor.execute("""
                INSERT INTO stock_movements (
                    nomenclature_id, operation_type, quantity, balance_after,
                    source_operation_type, source_operation_id,
                    idempotency_key, operation_date, metadata
                )
                SELECT 
                    ?, 'receipt', ?, 
                    COALESCE((SELECT quantity FROM stock_balances WHERE nomenclature_id = ?), 0) + ?,
                    'production_leftover', ?,
                    ?, GETUTCDATE(), ?
            """, mix_data.mix_nomenclature_id, mix_data.leftover_quantity,
                mix_data.mix_nomenclature_id, mix_data.leftover_quantity,
                batch.batch_number, leftover_key,
                json.dumps({
                    'batch_id': batch_id,
                    'batch_number': batch.batch_number,
                    'mix_type': 'leftover'
                }))
            
            # Update stock balance
            cursor.execute("""
                IF EXISTS (SELECT 1 FROM stock_balances WHERE nomenclature_id = ?)
                    UPDATE stock_balances
                    SET quantity = quantity + ?,
                        last_updated = GETUTCDATE()
                    WHERE nomenclature_id = ?
                ELSE
                    INSERT INTO stock_balances (nomenclature_id, quantity, last_updated)
                    VALUES (?, ?, GETUTCDATE())
            """, mix_data.mix_nomenclature_id, mix_data.leftover_quantity,
                mix_data.mix_nomenclature_id, mix_data.mix_nomenclature_id,
                mix_data.leftover_quantity)
        
        # If warehouse mix used, create withdrawal
        if mix_data.warehouse_mix_used > 0:
            warehouse_key = f"mix-warehouse-{batch_id}-{mix_data.idempotency_key}"
            
            # Check if enough stock
            cursor.execute(
                "SELECT quantity FROM stock_balances WHERE nomenclature_id = ?",
                mix_data.mix_nomenclature_id
            )
            result = cursor.fetchone()
            current_balance = float(result[0]) if result else 0
            
            if current_balance < mix_data.warehouse_mix_used:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient warehouse mix. Available: {current_balance}, Required: {mix_data.warehouse_mix_used}"
                )
            
            new_balance = current_balance - mix_data.warehouse_mix_used
            
            cursor.execute("""
                INSERT INTO stock_movements (
                    nomenclature_id, operation_type, quantity, balance_after,
                    source_operation_type, source_operation_id,
                    idempotency_key, operation_date, metadata
                )
                VALUES (?, 'withdrawal', ?, ?, 'production_use', ?, ?, GETUTCDATE(), ?)
            """, mix_data.mix_nomenclature_id, mix_data.warehouse_mix_used,
                new_balance, batch.batch_number, warehouse_key,
                json.dumps({
                    'batch_id': batch_id,
                    'batch_number': batch.batch_number,
                    'mix_type': 'warehouse_use'
                }))
            
            # Update stock balance
            cursor.execute("""
                UPDATE stock_balances
                SET quantity = ?,
                    last_updated = GETUTCDATE()
                WHERE nomenclature_id = ?
            """, new_balance, mix_data.mix_nomenclature_id)
        
        conn.commit()
        
        return {
            "message": "Mix produced successfully",
            "batch_id": batch_id,
            "produced_quantity": mix_data.produced_quantity,
            "used_quantity": mix_data.used_quantity,
            "leftover_quantity": mix_data.leftover_quantity,
            "warehouse_mix_used": mix_data.warehouse_mix_used
        }

@router.post("/batches/{batch_id}/materials/consume")
async def consume_materials(batch_id: int, materials: dict):
    """Consume materials (raw materials and spices) for batch production"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get batch
        cursor.execute("SELECT * FROM batches WHERE id = ?", batch_id)
        batch = cursor.fetchone()
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        consumed = []
        idempotency_key = materials.get('idempotency_key', f"consume-{batch_id}-{datetime.now().timestamp()}")
        
        for material in materials.get('materials', []):
            nomenclature_id = material['nomenclature_id']
            quantity = material['quantity']
            material_type = material.get('type', 'ingredient')
            
            # Check idempotency for this specific material
            material_key = f"{idempotency_key}-{nomenclature_id}"
            cursor.execute(
                "SELECT id FROM stock_movements WHERE idempotency_key = ?",
                material_key
            )
            if cursor.fetchone():
                continue  # Already consumed
            
            # Check stock availability
            cursor.execute(
                "SELECT quantity FROM stock_balances WHERE nomenclature_id = ?",
                nomenclature_id
            )
            result = cursor.fetchone()
            current_balance = float(result[0]) if result else 0
            
            if current_balance < quantity:
                cursor.execute(
                    "SELECT name FROM nomenclature WHERE id = ?",
                    nomenclature_id
                )
                name_result = cursor.fetchone()
                material_name = name_result[0] if name_result else f"ID {nomenclature_id}"
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient stock for {material_name}. Available: {current_balance}, Required: {quantity}"
                )
            
            new_balance = current_balance - quantity
            
            # Create withdrawal movement
            cursor.execute("""
                INSERT INTO stock_movements (
                    nomenclature_id, operation_type, quantity, balance_after,
                    source_operation_type, source_operation_id,
                    idempotency_key, operation_date, metadata
                )
                VALUES (?, 'withdrawal', ?, ?, 'production', ?, ?, GETUTCDATE(), ?)
            """, nomenclature_id, quantity, new_balance,
                batch.batch_number, material_key,
                json.dumps({
                    'batch_id': batch_id,
                    'batch_number': batch.batch_number,
                    'material_type': material_type
                }))
            
            # Update stock balance
            cursor.execute("""
                UPDATE stock_balances
                SET quantity = ?,
                    last_updated = GETUTCDATE()
                WHERE nomenclature_id = ?
            """, new_balance, nomenclature_id)
            
            # Record in batch_materials
            cursor.execute("""
                INSERT INTO batch_materials (
                    batch_id, nomenclature_id, material_type, quantity_used, notes
                )
                VALUES (?, ?, ?, ?, ?)
            """, batch_id, nomenclature_id, material_type, quantity,
                material.get('notes', ''))
            
            consumed.append({
                'nomenclature_id': nomenclature_id,
                'quantity': quantity,
                'material_type': material_type
            })
        
        conn.commit()
        
        return {
            "message": "Materials consumed successfully",
            "batch_id": batch_id,
            "consumed_count": len(consumed),
            "consumed_materials": consumed
        }


async def complete_batch(batch_id: int, completion: BatchComplete):
    """Complete a batch and create stock movements"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get batch
        cursor.execute("""
            SELECT b.*, r.target_product_id, r.expected_yield_min, r.expected_yield_max
            FROM batches b
            JOIN recipes r ON b.recipe_id = r.id
            WHERE b.id = ?
        """, batch_id)
        
        batch = cursor.fetchone()
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        if batch.status == 'completed':
            raise HTTPException(status_code=400, detail="Batch already completed")
        
        # Update batch
        cursor.execute("""
            UPDATE batches
            SET status = 'completed',
                final_weight = ?,
                completed_at = GETUTCDATE(),
                operator_notes = COALESCE(operator_notes, '') + ' ' + COALESCE(?, ''),
                updated_at = GETUTCDATE()
            WHERE id = ?
        """, completion.final_weight, completion.notes, batch_id)
        
        # Calculate yield percentage
        yield_percent = (completion.final_weight / float(batch.initial_weight)) * 100
        
        # Check if idempotency key already exists
        cursor.execute(
            "SELECT id FROM stock_movements WHERE idempotency_key = ?",
            completion.idempotency_key
        )
        if cursor.fetchone():
            # Already processed
            conn.commit()
            return {"message": "Batch already completed", "batch_id": batch_id}
        
        # Create stock receipt movement for finished product
        cursor.execute("""
            INSERT INTO stock_movements (
                nomenclature_id, operation_type, quantity, balance_after,
                source_operation_type, source_operation_id,
                idempotency_key, operation_date, metadata
            )
            SELECT 
                ?, 'receipt', ?, 
                COALESCE((SELECT quantity FROM stock_balances WHERE nomenclature_id = ?), 0) + ?,
                'production', ?,
                ?, GETUTCDATE(), ?
        """, batch.target_product_id, completion.final_weight,
            batch.target_product_id, completion.final_weight,
            batch.batch_number, completion.idempotency_key,
            json.dumps({
                'batch_id': batch_id,
                'batch_number': batch.batch_number,
                'yield_percent': round(yield_percent, 2)
            }))
        
        # Update stock balance
        cursor.execute("""
            IF EXISTS (SELECT 1 FROM stock_balances WHERE nomenclature_id = ?)
                UPDATE stock_balances
                SET quantity = quantity + ?,
                    last_updated = GETUTCDATE()
                WHERE nomenclature_id = ?
            ELSE
                INSERT INTO stock_balances (nomenclature_id, quantity, last_updated)
                VALUES (?, ?, GETUTCDATE())
        """, batch.target_product_id, completion.final_weight,
            batch.target_product_id, batch.target_product_id, completion.final_weight)
        
        conn.commit()
        
        return {
            "message": "Batch completed successfully",
            "batch_id": batch_id,
            "yield_percent": round(yield_percent, 2),
            "expected_range": f"{batch.expected_yield_min}-{batch.expected_yield_max}%"
        }
