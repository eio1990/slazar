"""
Production module API endpoints
"""
from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime
import json

from database import get_db_connection
from models import Recipe, RecipeStep, BatchCreate, Batch, BatchComplete, BatchOperationCreate

router = APIRouter(prefix="/api/production", tags=["production"])

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

@router.post("/batches", response_model=Batch)
async def create_batch(batch_data: BatchCreate):
    """Create new production batch"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Verify recipe exists
        cursor.execute("SELECT name FROM recipes WHERE id = ?", batch_data.recipe_id)
        recipe = cursor.fetchone()
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")
        
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

@router.put("/batches/{batch_id}/complete")
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
                completed_at = GETDATE(),
                operator_notes = COALESCE(operator_notes, '') + ' ' + COALESCE(?, ''),
                updated_at = GETDATE()
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
                ?, GETDATE(), ?
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
                    last_updated = GETDATE()
                WHERE nomenclature_id = ?
            ELSE
                INSERT INTO stock_balances (nomenclature_id, quantity, last_updated)
                VALUES (?, ?, GETDATE())
        """, batch.target_product_id, completion.final_weight,
            batch.target_product_id, batch.target_product_id, completion.final_weight)
        
        conn.commit()
        
        return {
            "message": "Batch completed successfully",
            "batch_id": batch_id,
            "yield_percent": round(yield_percent, 2),
            "expected_range": f"{batch.expected_yield_min}-{batch.expected_yield_max}%"
        }
