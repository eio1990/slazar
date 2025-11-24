"""
API для модуля розділки
"""
from fastapi import APIRouter, HTTPException
from typing import Optional, List
from decimal import Decimal
import json
from datetime import datetime

from database import get_db_connection
from butchery_models import (
    ButcheryRecipe, ButcheryRecipeOutput,
    ButcheryOperationCreate, ButcheryOperationComplete,
    ButcheryOperation, ButcheryOperationOutput
)
import os

# Timezone offset for local time (Ukraine/Kyiv is UTC+2 in winter, UTC+3 in summer)
# We use +2 as base offset
TIMEZONE_OFFSET_HOURS = 2

router = APIRouter(prefix="/butchery", tags=["butchery"])

@router.get("/recipes", response_model=List[ButcheryRecipe])
async def get_butchery_recipes(source_id: Optional[int] = None, level: Optional[int] = None):
    """
    Отримати список рецептів розділки
    - source_id: фільтр по сировині (що розділяємо)
    - level: фільтр по рівню (1 або 2)
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        query = """
            SELECT br.id, br.name, br.source_nomenclature_id, n.name as source_name,
                   br.description, br.level, br.is_active
            FROM butchery_recipes br
            JOIN nomenclature n ON br.source_nomenclature_id = n.id
            WHERE br.is_active = 1
        """
        params = []
        
        if source_id:
            query += " AND br.source_nomenclature_id = ?"
            params.append(source_id)
        
        if level:
            query += " AND br.level = ?"
            params.append(level)
        
        query += " ORDER BY br.level, br.name"
        
        cursor.execute(query, *params)
        recipes = []
        
        for row in cursor.fetchall():
            recipe_id = row.id
            
            # Отримати виходи рецепту
            cursor.execute("""
                SELECT bro.output_nomenclature_id, n.name, bro.yield_percentage,
                       bro.is_main_output, bro.output_type
                FROM butchery_recipe_outputs bro
                JOIN nomenclature n ON bro.output_nomenclature_id = n.id
                WHERE bro.recipe_id = ?
                ORDER BY bro.is_main_output DESC, bro.yield_percentage DESC
            """, recipe_id)
            
            outputs = []
            for out_row in cursor.fetchall():
                outputs.append(ButcheryRecipeOutput(
                    output_nomenclature_id=out_row[0],
                    output_name=out_row[1],
                    yield_percentage=float(out_row[2]),
                    is_main_output=out_row[3],
                    output_type=out_row[4]
                ))
            
            recipes.append(ButcheryRecipe(
                id=row.id,
                name=row.name,
                source_nomenclature_id=row.source_nomenclature_id,
                source_name=row.source_name,
                description=row.description,
                level=row.level,
                is_active=row.is_active,
                outputs=outputs
            ))
        
        return recipes


@router.get("/recipes/{recipe_id}", response_model=ButcheryRecipe)
async def get_butchery_recipe(recipe_id: int):
    """Деталі рецепту розділки з виходами"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT br.id, br.name, br.source_nomenclature_id, n.name as source_name,
                   br.description, br.level, br.is_active
            FROM butchery_recipes br
            JOIN nomenclature n ON br.source_nomenclature_id = n.id
            WHERE br.id = ?
        """, recipe_id)
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Рецепт розділки не знайдено")
        
        # Отримати виходи
        cursor.execute("""
            SELECT bro.output_nomenclature_id, n.name, bro.yield_percentage,
                   bro.is_main_output, bro.output_type
            FROM butchery_recipe_outputs bro
            JOIN nomenclature n ON bro.output_nomenclature_id = n.id
            WHERE bro.recipe_id = ?
            ORDER BY bro.is_main_output DESC, bro.yield_percentage DESC
        """, recipe_id)
        
        outputs = []
        for out_row in cursor.fetchall():
            outputs.append(ButcheryRecipeOutput(
                output_nomenclature_id=out_row[0],
                output_name=out_row[1],
                yield_percentage=float(out_row[2]),
                is_main_output=out_row[3],
                output_type=out_row[4]
            ))
        
        return ButcheryRecipe(
            id=row.id,
            name=row.name,
            source_nomenclature_id=row.source_nomenclature_id,
            source_name=row.source_name,
            description=row.description,
            level=row.level,
            is_active=row.is_active,
            outputs=outputs
        )


@router.post("/operations")
async def create_butchery_operation(operation: ButcheryOperationCreate):
    """
    Створити операцію розділки
    1. Перевірити наявність сировини на складі
    2. Списати сировину
    3. Створити запис операції
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Перевірити ідемпотентність
        cursor.execute("""
            SELECT id FROM butchery_operations WHERE idempotency_key = ?
        """, operation.idempotency_key)
        
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Операція вже створена")
        
        # Перевірити рецепт
        cursor.execute("SELECT name FROM butchery_recipes WHERE id = ?", operation.recipe_id)
        recipe = cursor.fetchone()
        if not recipe:
            raise HTTPException(status_code=404, detail="Рецепт розділки не знайдено")
        
        # Перевірити наявність сировини
        cursor.execute("""
            SELECT quantity FROM stock_balances WHERE nomenclature_id = ?
        """, operation.source_nomenclature_id)
        
        balance_row = cursor.fetchone()
        balance = float(balance_row[0]) if balance_row else 0
        
        if balance < operation.input_weight:
            cursor.execute("SELECT name FROM nomenclature WHERE id = ?", operation.source_nomenclature_id)
            name = cursor.fetchone()[0]
            raise HTTPException(
                status_code=400,
                detail=f"Недостатньо сировини '{name}'. Доступно: {balance:.2f} кг, Потрібно: {operation.input_weight:.2f} кг"
            )
        
        # Генерувати номер операції
        today = datetime.now().strftime("%y%m%d")
        cursor.execute("""
            SELECT COUNT(*) FROM butchery_operations 
            WHERE CONVERT(date, started_at) = CONVERT(date, DATEADD(HOUR, 2, GETDATE()))
        """)
        count = cursor.fetchone()[0] + 1
        operation_number = f"BUT-{today}-{count:03d}"
        
        # Списати сировину
        new_balance = balance - operation.input_weight
        
        # Stock movement
        cursor.execute("""
            INSERT INTO stock_movements (
                nomenclature_id, operation_type, quantity, balance_after,
                source_operation_type, source_operation_id,
                idempotency_key, operation_date, metadata
            )
            VALUES (?, 'withdrawal', ?, ?, 'butchery', ?, ?, DATEADD(HOUR, 2, GETDATE()), ?)
        """, operation.source_nomenclature_id, operation.input_weight, new_balance,
            operation_number, f"butchery-start-{operation.idempotency_key}",
            json.dumps({
                'operation_number': operation_number,
                'input_weight': operation.input_weight,
                'notes': operation.notes
            }))
        
        # Оновити баланс
        cursor.execute("""
            UPDATE stock_balances
            SET quantity = ?, last_updated = DATEADD(HOUR, 2, GETDATE())
            WHERE nomenclature_id = ?
        """, new_balance, operation.source_nomenclature_id)
        
        # Створити операцію розділки
        cursor.execute("""
            INSERT INTO butchery_operations (
                operation_number, recipe_id, source_nomenclature_id,
                input_weight, status, operator_notes, idempotency_key
            )
            VALUES (?, ?, ?, ?, 'in_progress', ?, ?)
        """, operation_number, operation.recipe_id, operation.source_nomenclature_id,
            operation.input_weight, operation.notes, operation.idempotency_key)
        
        operation_id = cursor.execute("SELECT @@IDENTITY").fetchone()[0]
        
        conn.commit()
        
        return {
            "message": "Операцію розділки розпочато",
            "operation_id": operation_id,
            "operation_number": operation_number,
            "input_weight": operation.input_weight
        }


@router.get("/operations")
async def get_butchery_operations(
    status: Optional[str] = None,
    limit: int = 50
):
    """Список операцій розділки"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        query = """
            SELECT bo.id, bo.operation_number, bo.recipe_id, br.name as recipe_name,
                   bo.source_nomenclature_id, n.name as source_name,
                   bo.input_weight, bo.status, bo.started_at, bo.completed_at,
                   bo.operator_notes
            FROM butchery_operations bo
            JOIN butchery_recipes br ON bo.recipe_id = br.id
            JOIN nomenclature n ON bo.source_nomenclature_id = n.id
            WHERE 1=1
        """
        params = []
        
        if status:
            query += " AND bo.status = ?"
            params.append(status)
        
        if limit:
            query = f"SELECT TOP {limit} * FROM ({query}) AS subquery ORDER BY started_at DESC"
        else:
            query += " ORDER BY bo.started_at DESC"
        
        cursor.execute(query, *params)
        
        operations = []
        for row in cursor.fetchall():
            operations.append(ButcheryOperation(
                id=row.id,
                operation_number=row.operation_number,
                recipe_id=row.recipe_id,
                recipe_name=row.recipe_name,
                source_nomenclature_id=row.source_nomenclature_id,
                source_name=row.source_name,
                input_weight=float(row.input_weight),
                status=row.status,
                started_at=row.started_at,
                completed_at=row.completed_at,
                operator_notes=row.operator_notes
            ))
        
        return operations


@router.get("/operations/{operation_id}")
async def get_butchery_operation(operation_id: int):
    """Деталі операції розділки з фактичними виходами"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Отримати операцію
        cursor.execute("""
            SELECT bo.id, bo.operation_number, bo.recipe_id, br.name as recipe_name,
                   bo.source_nomenclature_id, n.name as source_name,
                   bo.input_weight, bo.status, bo.started_at, bo.completed_at,
                   bo.operator_notes
            FROM butchery_operations bo
            JOIN butchery_recipes br ON bo.recipe_id = br.id
            JOIN nomenclature n ON bo.source_nomenclature_id = n.id
            WHERE bo.id = ?
        """, operation_id)
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Операцію не знайдено")
        
        operation = ButcheryOperation(
            id=row.id,
            operation_number=row.operation_number,
            recipe_id=row.recipe_id,
            recipe_name=row.recipe_name,
            source_nomenclature_id=row.source_nomenclature_id,
            source_name=row.source_name,
            input_weight=float(row.input_weight),
            status=row.status,
            started_at=row.started_at,
            completed_at=row.completed_at,
            operator_notes=row.operator_notes
        )
        
        # Отримати очікувані виходи з рецепту
        cursor.execute("""
            SELECT bro.output_nomenclature_id, n.name, bro.yield_percentage
            FROM butchery_recipe_outputs bro
            JOIN nomenclature n ON bro.output_nomenclature_id = n.id
            WHERE bro.recipe_id = ?
            ORDER BY bro.is_main_output DESC
        """, row.recipe_id)
        
        expected_outputs = []
        for out_row in cursor.fetchall():
            expected_weight = (float(row.input_weight) * float(out_row[2])) / 100
            expected_outputs.append({
                'output_nomenclature_id': out_row[0],
                'output_name': out_row[1],
                'expected_weight': round(expected_weight, 2),
                'yield_percentage': float(out_row[2])
            })
        
        # Отримати фактичні виходи (якщо є)
        cursor.execute("""
            SELECT boo.output_nomenclature_id, n.name, boo.expected_weight,
                   boo.actual_weight, boo.notes
            FROM butchery_operation_outputs boo
            JOIN nomenclature n ON boo.output_nomenclature_id = n.id
            WHERE boo.operation_id = ?
        """, operation_id)
        
        actual_outputs = []
        for out_row in cursor.fetchall():
            yield_pct = None
            if out_row[2]:  # expected_weight
                yield_pct = (float(out_row[3]) / float(out_row[2])) * 100
            
            actual_outputs.append(ButcheryOperationOutput(
                output_nomenclature_id=out_row[0],
                output_name=out_row[1],
                expected_weight=float(out_row[2]) if out_row[2] else None,
                actual_weight=float(out_row[3]),
                yield_percentage=round(yield_pct, 1) if yield_pct else None
            ))
        
        return {
            "operation": operation,
            "expected_outputs": expected_outputs,
            "actual_outputs": actual_outputs
        }


@router.put("/operations/{operation_id}/complete")
async def complete_butchery_operation(operation_id: int, completion: ButcheryOperationComplete):
    """
    Завершити розділку
    1. Записати фактичні виходи
    2. Оприбуткувати кожен вихід на склад
    3. Створити stock_movements
    4. Змінити статус на 'completed'
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Перевірити ідемпотентність
        cursor.execute("""
            SELECT status FROM butchery_operations WHERE id = ?
        """, operation_id)
        
        operation = cursor.fetchone()
        if not operation:
            raise HTTPException(status_code=404, detail="Операцію не знайдено")
        
        if operation[0] == 'completed':
            raise HTTPException(status_code=400, detail="Операція вже завершена")
        
        # Отримати інформацію про операцію
        cursor.execute("""
            SELECT operation_number, input_weight, recipe_id
            FROM butchery_operations WHERE id = ?
        """, operation_id)
        
        op_row = cursor.fetchone()
        operation_number = op_row[0]
        input_weight = float(op_row[1])
        recipe_id = op_row[2]
        
        # Фізична валідація: сума виходів не може перевищувати вхід
        total_output = sum(out.actual_weight for out in completion.outputs)
        if total_output > input_weight:
            raise HTTPException(
                status_code=400,
                detail=f"Помилка: сума виходів ({total_output:.2f} кг) перевищує вхідну вагу ({input_weight:.2f} кг). Це фізично неможливо."
            )
        
        # Отримати очікувані виходи та знайти стек (liquid-waste)
        cursor.execute("""
            SELECT bro.output_nomenclature_id, bro.yield_percentage, n.nomenclature_type
            FROM butchery_recipe_outputs bro
            JOIN nomenclature n ON bro.output_nomenclature_id = n.id
            WHERE bro.recipe_id = ?
        """, recipe_id)
        
        expected_outputs = {}
        liquid_waste_id = None
        for row in cursor.fetchall():
            expected_outputs[row[0]] = float(row[1])
            if row[2] == 'liquid-waste':
                liquid_waste_id = row[0]
        
        # Автоматично розрахувати стек (різниця між входом і сумою виходів)
        if liquid_waste_id:
            liquid_waste_weight = input_weight - total_output
            if liquid_waste_weight > 0:
                # Додати стек до виходів автоматично
                from butchery_models import ButcheryOutputInput
                liquid_waste_output = ButcheryOutputInput(
                    output_nomenclature_id=liquid_waste_id,
                    actual_weight=liquid_waste_weight,
                    notes="Автоматично розраховано"
                )
                completion.outputs.append(liquid_waste_output)
                total_output += liquid_waste_weight
        
        # Записати фактичні виходи та оприбуткувати
        for output in completion.outputs:
            expected_weight = None
            if output.output_nomenclature_id in expected_outputs:
                expected_weight = (input_weight * expected_outputs[output.output_nomenclature_id]) / 100
            
            # Записати вихід
            cursor.execute("""
                INSERT INTO butchery_operation_outputs (
                    operation_id, output_nomenclature_id, expected_weight, actual_weight, notes
                )
                VALUES (?, ?, ?, ?, ?)
            """, operation_id, output.output_nomenclature_id, expected_weight,
                output.actual_weight, output.notes)
            
            # Перевірити чи це стек (liquid-waste) - не оприбутковувати
            cursor.execute("""
                SELECT nomenclature_type FROM nomenclature WHERE id = ?
            """, output.output_nomenclature_id)
            
            nomenclature_type_row = cursor.fetchone()
            nomenclature_type = nomenclature_type_row[0] if nomenclature_type_row else None
            
            # Стек (кров і вода) не оприбутковується, тільки фіксується для аналітики
            if nomenclature_type == 'liquid-waste':
                continue
            
            # Пропустити виходи з нульовою вагою (не створювати записи в журналі)
            if output.actual_weight <= 0:
                continue
            
            # Оприбуткувати на склад (всі інші виходи)
            cursor.execute("""
                SELECT COALESCE(quantity, 0) FROM stock_balances 
                WHERE nomenclature_id = ?
            """, output.output_nomenclature_id)
            
            balance_row = cursor.fetchone()
            current_balance = float(balance_row[0]) if balance_row else 0
            new_balance = current_balance + output.actual_weight
            
            # Stock movement
            cursor.execute("""
                INSERT INTO stock_movements (
                    nomenclature_id, operation_type, quantity, balance_after,
                    source_operation_type, source_operation_id,
                    idempotency_key, operation_date, metadata
                )
                VALUES (?, 'receipt', ?, ?, 'butchery', ?, ?, DATEADD(HOUR, 2, GETDATE()), ?)
            """, output.output_nomenclature_id, output.actual_weight, new_balance,
                operation_number, f"butchery-output-{operation_id}-{output.output_nomenclature_id}",
                json.dumps({
                    'operation_id': operation_id,
                    'operation_number': operation_number,
                    'expected_weight': expected_weight,
                    'actual_weight': output.actual_weight
                }))
            
            # Оновити або створити баланс
            cursor.execute("""
                IF EXISTS (SELECT 1 FROM stock_balances WHERE nomenclature_id = ?)
                    UPDATE stock_balances 
                    SET quantity = ?, last_updated = DATEADD(HOUR, 2, GETDATE())
                    WHERE nomenclature_id = ?
                ELSE
                    INSERT INTO stock_balances (nomenclature_id, quantity, last_updated)
                    VALUES (?, ?, DATEADD(HOUR, 2, GETDATE()))
            """, output.output_nomenclature_id, new_balance, output.output_nomenclature_id,
                output.output_nomenclature_id, new_balance)
        
        # Завершити операцію
        cursor.execute("""
            UPDATE butchery_operations
            SET status = 'completed',
                completed_at = DATEADD(HOUR, 2, GETDATE()),
                operator_notes = COALESCE(?, operator_notes)
            WHERE id = ?
        """, completion.notes, operation_id)
        
        conn.commit()
        
        return {
            "message": "Розділку завершено успішно",
            "operation_id": operation_id,
            "operation_number": operation_number,
            "outputs_count": len(completion.outputs),
            "total_output_weight": total_output
        }
