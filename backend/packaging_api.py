"""
Packaging module API endpoints
Модуль фасовки весовой готовой продукции
"""
from fastapi import APIRouter, HTTPException
from typing import List, Optional
from datetime import datetime
import json

from database import get_db_connection
from models import (
    PackagingRecipe, PackagingRecipeMaterial,
    PackagingBatchCreate, PackagingBatch, PackagingBatchComplete,
    PackagingOperationCreate, PackagingOperation
)

router = APIRouter(prefix="/api/packaging", tags=["packaging"])


@router.get("/recipes", response_model=List[PackagingRecipe])
async def get_packaging_recipes(
    source_product_id: Optional[int] = None,
    packaging_type: Optional[str] = None,
    active_only: bool = True
):
    """Получить список рецептов фасовки с нормами расхода материалов"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        query = """
            SELECT 
                pr.id, pr.source_product_id, pr.target_product_id,
                pr.packaging_type, pr.target_weight_grams, pr.is_active, pr.notes,
                n1.name as source_name, n2.name as target_name
            FROM packaging_recipes pr
            JOIN nomenclature n1 ON pr.source_product_id = n1.id
            JOIN nomenclature n2 ON pr.target_product_id = n2.id
            WHERE 1=1
        """
        params = []
        
        if active_only:
            query += " AND pr.is_active = 1"
        
        if source_product_id:
            query += " AND pr.source_product_id = ?"
            params.append(source_product_id)
        
        if packaging_type:
            query += " AND pr.packaging_type = ?"
            params.append(packaging_type)
        
        query += " ORDER BY n1.name, pr.packaging_type, pr.target_weight_grams"
        
        cursor.execute(query, *params)
        
        recipes = []
        for row in cursor.fetchall():
            recipe_id = row.id
            
            # Получаем материалы для рецепта
            cursor.execute("""
                SELECT 
                    prm.material_id, prm.quantity_per_unit, prm.rounding_precision,
                    prm.material_type, n.name as material_name
                FROM packaging_recipe_materials prm
                JOIN nomenclature n ON prm.material_id = n.id
                WHERE prm.recipe_id = ?
            """, recipe_id)
            
            materials = []
            for mat_row in cursor.fetchall():
                materials.append(PackagingRecipeMaterial(
                    material_id=mat_row.material_id,
                    material_name=mat_row.material_name,
                    quantity_per_unit=float(mat_row.quantity_per_unit),
                    rounding_precision=float(mat_row.rounding_precision) if mat_row.rounding_precision else None,
                    material_type=mat_row.material_type
                ))
            
            recipes.append(PackagingRecipe(
                id=recipe_id,
                source_product_id=row.source_product_id,
                source_product_name=row.source_name,
                target_product_id=row.target_product_id,
                target_product_name=row.target_name,
                packaging_type=row.packaging_type,
                target_weight_grams=row.target_weight_grams,
                is_active=bool(row.is_active),
                materials=materials,
                notes=row.notes
            ))
        
        return recipes


@router.post("/batches", response_model=PackagingBatch)
async def create_packaging_batch(batch_data: PackagingBatchCreate):
    """Создать партию фасовки (запуск цикла фасовки)"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Проверяем idempotency
        cursor.execute("""
            SELECT id FROM packaging_batches WHERE batch_number = ?
        """, batch_data.idempotency_key)
        
        existing = cursor.fetchone()
        if existing:
            # Возвращаем существующую партию
            return await get_packaging_batch(existing.id)
        
        # Получаем рецепт фасовки
        cursor.execute("""
            SELECT pr.*, n1.name as source_name, n2.name as target_name
            FROM packaging_recipes pr
            JOIN nomenclature n1 ON pr.source_product_id = n1.id
            JOIN nomenclature n2 ON pr.target_product_id = n2.id
            WHERE pr.id = ? AND pr.is_active = 1
        """, batch_data.recipe_id)
        
        recipe = cursor.fetchone()
        if not recipe:
            raise HTTPException(status_code=404, detail="Рецепт фасовки не найден или не активен")
        
        # Проверяем доступность весового продукта на складе
        cursor.execute("""
            SELECT COALESCE(quantity, 0) as quantity
            FROM stock_balances
            WHERE nomenclature_id = ?
        """, recipe.source_product_id)
        
        balance_row = cursor.fetchone()
        source_balance = float(balance_row[0]) if balance_row else 0
        
        if source_balance < batch_data.source_weight_taken:
            raise HTTPException(
                status_code=400,
                detail=f"Недостатньо весової продукції на складі. Доступно: {source_balance:.2f} кг, Потрібно: {batch_data.source_weight_taken:.2f} кг"
            )
        
        # Генерируем номер партии фасовки
        today = datetime.now().strftime("%d%m%Y")
        
        # Получаем счетчик партий на сегодня для данного продукта
        cursor.execute("""
            SELECT COUNT(*) 
            FROM packaging_batches 
            WHERE batch_number LIKE ?
        """, f"PKG-{recipe.source_product_id}-{today}-%")
        
        count = cursor.fetchone()[0]
        batch_number = f"PKG-{recipe.source_product_id}-{today}-{count + 1:03d}"
        
        # Создаем партию фасовки
        cursor.execute("""
            INSERT INTO packaging_batches (
                batch_number, recipe_id, source_product_id, target_product_id,
                status, planned_quantity, source_weight_taken,
                operator_notes, started_at
            )
            VALUES (?, ?, ?, ?, 'in_progress', ?, ?, ?, GETUTCDATE())
        """, batch_number, batch_data.recipe_id, recipe.source_product_id,
            recipe.target_product_id, batch_data.planned_quantity,
            batch_data.source_weight_taken, batch_data.notes)
        
        batch_id = int(cursor.execute("SELECT @@IDENTITY").fetchone()[0])
        
        conn.commit()
        
        return await get_packaging_batch(batch_id)


@router.get("/batches", response_model=List[PackagingBatch])
async def get_packaging_batches(
    status: Optional[str] = None,
    source_product_id: Optional[int] = None,
    limit: int = 100
):
    """Получить список партий фасовки"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        query = """
            SELECT 
                pb.id, pb.batch_number, pb.recipe_id,
                pb.source_product_id, pb.target_product_id,
                pb.status, pb.planned_quantity, pb.source_weight_taken,
                pb.actual_packed_quantity, pb.actual_source_used, pb.waste_quantity,
                pb.started_at, pb.completed_at, pb.operator_notes,
                n1.name as source_name, n2.name as target_name,
                pr.packaging_type, pr.target_weight_grams
            FROM packaging_batches pb
            JOIN nomenclature n1 ON pb.source_product_id = n1.id
            JOIN nomenclature n2 ON pb.target_product_id = n2.id
            JOIN packaging_recipes pr ON pb.recipe_id = pr.id
            WHERE 1=1
        """
        params = []
        
        if status:
            query += " AND pb.status = ?"
            params.append(status)
        
        if source_product_id:
            query += " AND pb.source_product_id = ?"
            params.append(source_product_id)
        
        query += " ORDER BY pb.started_at DESC"
        
        if limit:
            query = f"SELECT TOP {limit} * FROM ({query}) AS subquery ORDER BY started_at DESC"
        
        cursor.execute(query, *params)
        
        batches = []
        for row in cursor.fetchall():
            batches.append(PackagingBatch(
                id=row.id,
                batch_number=row.batch_number,
                recipe_id=row.recipe_id,
                source_product_id=row.source_product_id,
                source_product_name=row.source_name,
                target_product_id=row.target_product_id,
                target_product_name=row.target_name,
                packaging_type=row.packaging_type,
                target_weight_grams=row.target_weight_grams,
                status=row.status,
                planned_quantity=row.planned_quantity,
                source_weight_taken=float(row.source_weight_taken),
                actual_packed_quantity=row.actual_packed_quantity,
                actual_source_used=float(row.actual_source_used),
                waste_quantity=float(row.waste_quantity),
                started_at=row.started_at,
                completed_at=row.completed_at,
                operator_notes=row.operator_notes
            ))
        
        return batches


@router.get("/batches/{batch_id}", response_model=PackagingBatch)
async def get_packaging_batch(batch_id: int):
    """Получить детали партии фасовки"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                pb.id, pb.batch_number, pb.recipe_id,
                pb.source_product_id, pb.target_product_id,
                pb.status, pb.planned_quantity, pb.source_weight_taken,
                pb.actual_packed_quantity, pb.actual_source_used, pb.waste_quantity,
                pb.started_at, pb.completed_at, pb.operator_notes,
                n1.name as source_name, n2.name as target_name,
                pr.packaging_type, pr.target_weight_grams
            FROM packaging_batches pb
            JOIN nomenclature n1 ON pb.source_product_id = n1.id
            JOIN nomenclature n2 ON pb.target_product_id = n2.id
            JOIN packaging_recipes pr ON pb.recipe_id = pr.id
            WHERE pb.id = ?
        """, batch_id)
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Партия фасовки не найдена")
        
        return PackagingBatch(
            id=row.id,
            batch_number=row.batch_number,
            recipe_id=row.recipe_id,
            source_product_id=row.source_product_id,
            source_product_name=row.source_name,
            target_product_id=row.target_product_id,
            target_product_name=row.target_name,
            packaging_type=row.packaging_type,
            target_weight_grams=row.target_weight_grams,
            status=row.status,
            planned_quantity=row.planned_quantity,
            source_weight_taken=float(row.source_weight_taken),
            actual_packed_quantity=row.actual_packed_quantity,
            actual_source_used=float(row.actual_source_used),
            waste_quantity=float(row.waste_quantity),
            started_at=row.started_at,
            completed_at=row.completed_at,
            operator_notes=row.operator_notes
        )


@router.post("/batches/{batch_id}/operations")
async def record_packaging_operation(batch_id: int, operation_data: PackagingOperationCreate):
    """Записать операцию фасовки (фиксация факта)"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Получаем партию
        cursor.execute("SELECT * FROM packaging_batches WHERE id = ?", batch_id)
        batch = cursor.fetchone()
        if not batch:
            raise HTTPException(status_code=404, detail="Партия фасовки не найдена")
        
        if batch.status == 'completed':
            raise HTTPException(status_code=400, detail="Партия уже завершена")
        
        # Проверяем idempotency
        cursor.execute("""
            SELECT id FROM packaging_operations WHERE idempotency_key = ?
        """, operation_data.idempotency_key)
        
        if cursor.fetchone():
            return {"message": "Операция уже записана", "batch_id": batch_id}
        
        # Получаем рецепт
        cursor.execute("SELECT * FROM packaging_recipes WHERE id = ?", batch.recipe_id)
        recipe = cursor.fetchone()
        
        # Проверяем доступность материалов
        for material in operation_data.materials_used:
            material_id = material['material_id']
            quantity = material['quantity']
            
            cursor.execute("""
                SELECT COALESCE(quantity, 0) FROM stock_balances WHERE nomenclature_id = ?
            """, material_id)
            
            balance_row = cursor.fetchone()
            balance = float(balance_row[0]) if balance_row else 0
            
            if balance < quantity:
                cursor.execute("SELECT name FROM nomenclature WHERE id = ?", material_id)
                name = cursor.fetchone()[0]
                raise HTTPException(
                    status_code=400,
                    detail=f"Недостатньо матеріалу '{name}'. Доступно: {balance:.2f}, Потрібно: {quantity:.2f}"
                )
        
        # Создаем операцию
        cursor.execute("""
            INSERT INTO packaging_operations (
                batch_id, operation_type, packed_quantity, source_used,
                waste_quantity, notes, idempotency_key
            )
            VALUES (?, 'pack', ?, ?, ?, ?, ?)
        """, batch_id, operation_data.packed_quantity, operation_data.source_used,
            operation_data.waste_quantity, operation_data.notes, operation_data.idempotency_key)
        
        operation_id = int(cursor.execute("SELECT @@IDENTITY").fetchone()[0])
        
        # Списываем материалы
        for material in operation_data.materials_used:
            material_id = material['material_id']
            quantity = material['quantity']
            
            # Получаем текущий баланс
            cursor.execute("""
                SELECT COALESCE(quantity, 0) FROM stock_balances WHERE nomenclature_id = ?
            """, material_id)
            current_balance = float(cursor.fetchone()[0])
            new_balance = current_balance - quantity
            
            # Создаем движение
            movement_key = f"packaging-material-{batch_id}-{material_id}-{operation_data.idempotency_key}"
            
            cursor.execute("""
                INSERT INTO stock_movements (
                    nomenclature_id, operation_type, quantity, balance_after,
                    source_operation_type, source_operation_id,
                    idempotency_key, operation_date, metadata
                )
                VALUES (?, 'withdrawal', ?, ?, 'packaging_material', ?, ?, GETUTCDATE(), ?)
            """, material_id, quantity, new_balance, batch.batch_number, movement_key,
                json.dumps({
                    'batch_id': batch_id,
                    'batch_number': batch.batch_number,
                    'operation_id': operation_id
                }))
            
            movement_id = int(cursor.execute("SELECT @@IDENTITY").fetchone()[0])
            
            # Обновляем баланс
            cursor.execute("""
                UPDATE stock_balances
                SET quantity = ?, last_updated = GETUTCDATE()
                WHERE nomenclature_id = ?
            """, new_balance, material_id)
            
            # Записываем расход материала
            cursor.execute("""
                INSERT INTO packaging_material_consumption (
                    operation_id, material_id, quantity_used, movement_id
                )
                VALUES (?, ?, ?, ?)
            """, operation_id, material_id, quantity, movement_id)
        
        # Обновляем итоги партии
        cursor.execute("""
            UPDATE packaging_batches
            SET actual_packed_quantity = actual_packed_quantity + ?,
                actual_source_used = actual_source_used + ?,
                waste_quantity = waste_quantity + ?,
                updated_at = GETUTCDATE()
            WHERE id = ?
        """, operation_data.packed_quantity, operation_data.source_used,
            operation_data.waste_quantity, batch_id)
        
        conn.commit()
        
        return {
            "message": "Операція записана успішно",
            "batch_id": batch_id,
            "operation_id": operation_id,
            "packed_quantity": operation_data.packed_quantity
        }


@router.put("/batches/{batch_id}/complete")
async def complete_packaging_batch(batch_id: int, completion: PackagingBatchComplete):
    """Завершить партию фасовки"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Получаем партию
        cursor.execute("SELECT * FROM packaging_batches WHERE id = ?", batch_id)
        batch = cursor.fetchone()
        if not batch:
            raise HTTPException(status_code=404, detail="Партия фасовки не найдена")
        
        if batch.status == 'completed':
            raise HTTPException(status_code=400, detail="Партия уже завершена")
        
        # Обновляем партию
        cursor.execute("""
            UPDATE packaging_batches
            SET status = 'completed',
                actual_packed_quantity = ?,
                actual_source_used = ?,
                waste_quantity = ?,
                operator_notes = ?,
                completed_at = GETUTCDATE(),
                updated_at = GETUTCDATE()
            WHERE id = ?
        """, completion.final_packed_quantity, completion.final_source_used,
            completion.final_waste, completion.notes, batch_id)
        
        # Списываем весовой продукт (если еще не списан)
        source_withdrawal_key = f"packaging-source-{batch_id}-{completion.idempotency_key}"
        
        cursor.execute("""
            SELECT id FROM stock_movements WHERE idempotency_key = ?
        """, source_withdrawal_key)
        
        if not cursor.fetchone():
            # Получаем баланс
            cursor.execute("""
                SELECT COALESCE(quantity, 0) FROM stock_balances 
                WHERE nomenclature_id = ?
            """, batch.source_product_id)
            
            source_balance = float(cursor.fetchone()[0])
            new_balance = source_balance - completion.final_source_used
            
            # Создаем движение
            cursor.execute("""
                INSERT INTO stock_movements (
                    nomenclature_id, operation_type, quantity, balance_after,
                    source_operation_type, source_operation_id,
                    idempotency_key, operation_date, metadata
                )
                VALUES (?, 'withdrawal', ?, ?, 'packaging_source', ?, ?, GETUTCDATE(), ?)
            """, batch.source_product_id, completion.final_source_used, new_balance,
                batch.batch_number, source_withdrawal_key,
                json.dumps({
                    'batch_id': batch_id,
                    'batch_number': batch.batch_number,
                    'packed_quantity': completion.final_packed_quantity
                }))
            
            # Обновляем баланс
            cursor.execute("""
                UPDATE stock_balances
                SET quantity = ?, last_updated = GETUTCDATE()
                WHERE nomenclature_id = ?
            """, new_balance, batch.source_product_id)
        
        # Оприходуем фасованную продукцию
        receipt_key = f"packaging-receipt-{batch_id}-{completion.idempotency_key}"
        
        cursor.execute("""
            SELECT id FROM stock_movements WHERE idempotency_key = ?
        """, receipt_key)
        
        if not cursor.fetchone():
            # Получаем баланс фасованной продукции
            cursor.execute("""
                SELECT COALESCE(quantity, 0) FROM stock_balances 
                WHERE nomenclature_id = ?
            """, batch.target_product_id)
            
            result = cursor.fetchone()
            target_balance = float(result[0]) if result else 0
            new_target_balance = target_balance + completion.final_packed_quantity
            
            # Создаем приход
            cursor.execute("""
                INSERT INTO stock_movements (
                    nomenclature_id, operation_type, quantity, balance_after,
                    source_operation_type, source_operation_id,
                    idempotency_key, operation_date, metadata
                )
                VALUES (?, 'receipt', ?, ?, 'packaging_output', ?, ?, GETUTCDATE(), ?)
            """, batch.target_product_id, completion.final_packed_quantity, new_target_balance,
                batch.batch_number, receipt_key,
                json.dumps({
                    'batch_id': batch_id,
                    'batch_number': batch.batch_number,
                    'source_used': completion.final_source_used
                }))
            
            # Обновляем/создаем баланс
            cursor.execute("""
                IF EXISTS (SELECT 1 FROM stock_balances WHERE nomenclature_id = ?)
                    UPDATE stock_balances
                    SET quantity = ?, last_updated = GETUTCDATE()
                    WHERE nomenclature_id = ?
                ELSE
                    INSERT INTO stock_balances (nomenclature_id, quantity, last_updated)
                    VALUES (?, ?, GETUTCDATE())
            """, batch.target_product_id, new_target_balance, batch.target_product_id,
                batch.target_product_id, new_target_balance)
        
        conn.commit()
        
        return {
            "message": "Партію фасовки завершено",
            "batch_id": batch_id,
            "batch_number": batch.batch_number,
            "packed_quantity": completion.final_packed_quantity,
            "source_used": completion.final_source_used,
            "waste": completion.final_waste
        }


@router.get("/batches/{batch_id}/operations", response_model=List[PackagingOperation])
async def get_batch_operations(batch_id: int):
    """Получить список операций партии фасовки"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, batch_id, operation_type, packed_quantity,
                   source_used, waste_quantity, notes, created_at
            FROM packaging_operations
            WHERE batch_id = ?
            ORDER BY created_at
        """, batch_id)
        
        operations = []
        for row in cursor.fetchall():
            operations.append(PackagingOperation(
                id=row.id,
                batch_id=row.batch_id,
                operation_type=row.operation_type,
                packed_quantity=row.packed_quantity,
                source_used=float(row.source_used),
                waste_quantity=float(row.waste_quantity),
                notes=row.notes,
                created_at=row.created_at
            ))
        
        return operations
