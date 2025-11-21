"""
Packaging module API endpoints - SESSION-BASED WORKFLOW
Модуль фасовки с гибким подходом: одна сессия → много разных SKU
"""
from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
import json

from database import get_db_connection

router = APIRouter(prefix="/api/packaging", tags=["packaging"])

# ========== PYDANTIC MODELS FOR NEW SESSION WORKFLOW ==========

class PackagingSessionCreate(BaseModel):
    source_product_id: int
    source_weight_taken: float  # кг
    notes: Optional[str] = None

class PackagingSessionOutputCreate(BaseModel):
    target_product_id: int  # готовый SKU (например "Бастурма 100г вакуум")
    quantity_packed: int  # количество упаковок
    confirmed_materials: Optional[dict] = None  # оператор может подтвердить/скорректировать брак
    defect_quantity: int = 0  # брак
    notes: Optional[str] = None

class PackagingSessionRemainderCreate(BaseModel):
    nomenclature_id: int  # номенклатура остатка (например "Специи упавшие")
    weight_kg: float
    description: Optional[str] = None
    notes: Optional[str] = None

class PackagingSessionWasteCreate(BaseModel):
    waste_weight_kg: float
    waste_description: Optional[str] = None
    notes: Optional[str] = None

class PackagingSessionComplete(BaseModel):
    notes: Optional[str] = None

# ========== RECIPES ENDPOINT (unchanged) ==========

@router.get("/recipes")
async def get_packaging_recipes(source_product_id: Optional[int] = None):
    """Получить рецепты фасовки (для расчета материалов)"""
    def _get():
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
                WHERE pr.is_active = 1
            """
            params = []
            
            if source_product_id:
                query += " AND pr.source_product_id = ?"
                params.append(source_product_id)
            
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
                    materials.append({
                        'material_id': mat_row.material_id,
                        'material_name': mat_row.material_name,
                        'quantity_per_unit': float(mat_row.quantity_per_unit),
                        'rounding_precision': float(mat_row.rounding_precision) if mat_row.rounding_precision else None,
                        'material_type': mat_row.material_type
                    })
                
                recipes.append({
                    'id': recipe_id,
                    'source_product_id': row.source_product_id,
                    'source_product_name': row.source_name,
                    'target_product_id': row.target_product_id,
                    'target_product_name': row.target_name,
                    'packaging_type': row.packaging_type,
                    'target_weight_grams': row.target_weight_grams,
                    'is_active': bool(row.is_active),
                    'materials': materials,
                    'notes': row.notes
                })
            
            return recipes
    
    return await run_in_threadpool(_get)

# ========== SESSION ENDPOINTS ==========

@router.post("/sessions")
async def create_packaging_session(session_data: PackagingSessionCreate):
    """
    Создать новую сессию фасовки
    1. Списать весовой продукт со склада
    2. Создать запись сессии
    """
    def _create():
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Проверить наличность на складе
            cursor.execute("""
                SELECT COALESCE(quantity, 0) FROM stock_balances 
                WHERE nomenclature_id = ?
            """, session_data.source_product_id)
            
            balance_row = cursor.fetchone()
            balance = float(balance_row[0]) if balance_row else 0
            
            if balance < session_data.source_weight_taken:
                cursor.execute("SELECT name FROM nomenclature WHERE id = ?", session_data.source_product_id)
                product_name = cursor.fetchone()[0]
                raise HTTPException(
                    status_code=400,
                    detail=f"Недостатньо продукту '{product_name}'. Доступно: {balance:.2f} кг, Потрібно: {session_data.source_weight_taken:.2f} кг"
                )
            
            # Генерировать номер сессии
            today = datetime.now().strftime("%d%m%Y")
            cursor.execute("""
                SELECT COUNT(*) FROM packaging_sessions 
                WHERE session_number LIKE ?
            """, f"PKG-{today}-%")
            count = cursor.fetchone()[0]
            session_number = f"PKG-{today}-{count + 1:03d}"
            
            # Списать продукт со склада
            new_balance = balance - session_data.source_weight_taken
            
            # Stock movement
            movement_key = f"packaging-session-start-{session_number}-{datetime.now().timestamp()}"
            cursor.execute("""
                INSERT INTO stock_movements (
                    nomenclature_id, operation_type, quantity, balance_after,
                    source_operation_type, source_operation_id,
                    idempotency_key, operation_date, metadata
                )
                VALUES (?, 'withdrawal', ?, ?, 'packaging_session', ?, ?, DATEADD(HOUR, 2, GETDATE()), ?)
            """, session_data.source_product_id, session_data.source_weight_taken, new_balance,
                session_number, movement_key,
                json.dumps({
                    'session_number': session_number,
                    'source_weight_taken': session_data.source_weight_taken
                }))
            
            # Обновить баланс
            cursor.execute("""
                UPDATE stock_balances 
                SET quantity = ?, last_updated = DATEADD(HOUR, 2, GETDATE())
                WHERE nomenclature_id = ?
            """, new_balance, session_data.source_product_id)
            
            # Создать сессию
            cursor.execute("""
                INSERT INTO packaging_sessions (
                    session_number, source_product_id, source_weight_taken,
                    status, operator_notes
                )
                VALUES (?, ?, ?, 'in_progress', ?)
            """, session_number, session_data.source_product_id, 
                session_data.source_weight_taken, session_data.notes)
            
            session_id = int(cursor.execute("SELECT @@IDENTITY").fetchone()[0])
            
            conn.commit()
            
            return {
                "message": "Сесію фасування створено",
                "session_id": session_id,
                "session_number": session_number,
                "source_weight_taken": session_data.source_weight_taken
            }
    
    return await run_in_threadpool(_create)


@router.get("/sessions")
async def get_packaging_sessions(status: Optional[str] = None, limit: int = 50):
    """Получить список сессий фасовки"""
    def _get():
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT 
                    ps.id, ps.session_number, ps.source_product_id, ps.source_weight_taken,
                    ps.status, ps.started_at, ps.completed_at, ps.operator_notes,
                    n.name as source_product_name
                FROM packaging_sessions ps
                JOIN nomenclature n ON ps.source_product_id = n.id
                WHERE 1=1
            """
            params = []
            
            if status:
                query += " AND ps.status = ?"
                params.append(status)
            
            query = f"SELECT TOP {limit} * FROM ({query}) AS subquery ORDER BY started_at DESC"
            
            cursor.execute(query, *params)
            
            sessions = []
            for row in cursor.fetchall():
                session_id = row.id
                
                # Получить количество выходов
                cursor.execute("SELECT COUNT(*) FROM packaging_session_outputs WHERE session_id = ?", session_id)
                outputs_count = cursor.fetchone()[0]
                
                # Получить суммарное количество упакованных единиц
                cursor.execute("SELECT COALESCE(SUM(quantity_packed), 0) FROM packaging_session_outputs WHERE session_id = ?", session_id)
                total_packed = cursor.fetchone()[0]
                
                sessions.append({
                    'id': session_id,
                    'session_number': row.session_number,
                    'source_product_id': row.source_product_id,
                    'source_product_name': row.source_product_name,
                    'source_weight_taken': float(row.source_weight_taken),
                    'status': row.status,
                    'started_at': row.started_at.isoformat() if row.started_at else None,
                    'completed_at': row.completed_at.isoformat() if row.completed_at else None,
                    'operator_notes': row.operator_notes,
                    'outputs_count': outputs_count,
                    'total_packed': total_packed
                })
            
            return sessions
    
    return await run_in_threadpool(_get)


@router.get("/sessions/{session_id}")
async def get_packaging_session(session_id: int):
    """Получить детали сессии фасовки с выходами, остатками и отходами"""
    def _get():
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Получить сессию
            cursor.execute("""
                SELECT 
                    ps.id, ps.session_number, ps.source_product_id, ps.source_weight_taken,
                    ps.status, ps.started_at, ps.completed_at, ps.operator_notes,
                    n.name as source_product_name
                FROM packaging_sessions ps
                JOIN nomenclature n ON ps.source_product_id = n.id
                WHERE ps.id = ?
            """, session_id)
            
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Сесію фасування не знайдено")
            
            session = {
                'id': row.id,
                'session_number': row.session_number,
                'source_product_id': row.source_product_id,
                'source_product_name': row.source_product_name,
                'source_weight_taken': float(row.source_weight_taken),
                'status': row.status,
                'started_at': row.started_at.isoformat() if row.started_at else None,
                'completed_at': row.completed_at.isoformat() if row.completed_at else None,
                'operator_notes': row.operator_notes
            }
            
            # Получить выходы (outputs)
            cursor.execute("""
                SELECT 
                    pso.id, pso.target_product_id, pso.quantity_packed, 
                    pso.calculated_materials, pso.confirmed_materials, pso.defect_quantity,
                    pso.notes, pso.created_at, n.name as target_product_name
                FROM packaging_session_outputs pso
                JOIN nomenclature n ON pso.target_product_id = n.id
                WHERE pso.session_id = ?
                ORDER BY pso.created_at
            """, session_id)
            
            outputs = []
            for out_row in cursor.fetchall():
                outputs.append({
                    'id': out_row.id,
                    'target_product_id': out_row.target_product_id,
                    'target_product_name': out_row.target_product_name,
                    'quantity_packed': out_row.quantity_packed,
                    'calculated_materials': json.loads(out_row.calculated_materials) if out_row.calculated_materials else None,
                    'confirmed_materials': json.loads(out_row.confirmed_materials) if out_row.confirmed_materials else None,
                    'defect_quantity': out_row.defect_quantity,
                    'notes': out_row.notes,
                    'created_at': out_row.created_at.isoformat() if out_row.created_at else None
                })
            
            session['outputs'] = outputs
            
            # Получить остатки (remainders)
            cursor.execute("""
                SELECT 
                    psr.id, psr.nomenclature_id, psr.weight_kg, psr.description,
                    psr.notes, psr.created_at, n.name as nomenclature_name
                FROM packaging_session_remainders psr
                JOIN nomenclature n ON psr.nomenclature_id = n.id
                WHERE psr.session_id = ?
                ORDER BY psr.created_at
            """, session_id)
            
            remainders = []
            for rem_row in cursor.fetchall():
                remainders.append({
                    'id': rem_row.id,
                    'nomenclature_id': rem_row.nomenclature_id,
                    'nomenclature_name': rem_row.nomenclature_name,
                    'weight_kg': float(rem_row.weight_kg),
                    'description': rem_row.description,
                    'notes': rem_row.notes,
                    'created_at': rem_row.created_at.isoformat() if rem_row.created_at else None
                })
            
            session['remainders'] = remainders
            
            # Получить отходы (waste)
            cursor.execute("""
                SELECT id, waste_weight_kg, waste_description, notes, created_at
                FROM packaging_session_waste
                WHERE session_id = ?
                ORDER BY created_at
            """, session_id)
            
            waste_items = []
            for waste_row in cursor.fetchall():
                waste_items.append({
                    'id': waste_row.id,
                    'waste_weight_kg': float(waste_row.waste_weight_kg),
                    'waste_description': waste_row.waste_description,
                    'notes': waste_row.notes,
                    'created_at': waste_row.created_at.isoformat() if waste_row.created_at else None
                })
            
            session['waste'] = waste_items
            
            return session
    
    return await run_in_threadpool(_get)


@router.post("/sessions/{session_id}/outputs")
async def add_packaging_output(session_id: int, output_data: PackagingSessionOutputCreate):
    """
    Добавить выход (готовую продукцию) в сессию
    1. Найти рецепт для этого продукта
    2. Рассчитать материалы автоматически
    3. Списать материалы со склада
    4. Оприходовать готовую продукцию
    """
    def _add():
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Проверить сессию
            cursor.execute("SELECT status, session_number FROM packaging_sessions WHERE id = ?", session_id)
            session = cursor.fetchone()
            if not session:
                raise HTTPException(status_code=404, detail="Сесію не знайдено")
            
            if session.status == 'completed':
                raise HTTPException(status_code=400, detail="Сесія вже завершена")
            
            # Найти рецепт для целевого продукта
            cursor.execute("""
                SELECT pr.id, pr.source_product_id
                FROM packaging_recipes pr
                WHERE pr.target_product_id = ? AND pr.is_active = 1
            """, output_data.target_product_id)
            
            recipe = cursor.fetchone()
            if not recipe:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Рецепт фасування для продукту з ID {output_data.target_product_id} не знайдено"
                )
            
            # Получить материалы рецепта
            cursor.execute("""
                SELECT prm.material_id, prm.quantity_per_unit, prm.rounding_precision, 
                       prm.material_type, n.name, n.unit
                FROM packaging_recipe_materials prm
                JOIN nomenclature n ON prm.material_id = n.id
                WHERE prm.recipe_id = ?
            """, recipe.id)
            
            recipe_materials = cursor.fetchall()
            
            # АВТОМАТИЧЕСКИЙ РАСЧЕТ материалов
            calculated_materials = []
            
            for mat_row in recipe_materials:
                material_id = mat_row.material_id
                quantity_per_unit = float(mat_row.quantity_per_unit)
                rounding_precision = float(mat_row.rounding_precision) if mat_row.rounding_precision else None
                material_type = mat_row.material_type
                material_name = mat_row.name
                material_unit = mat_row.unit
                
                # Рассчитываем количество
                calculated_qty = quantity_per_unit * output_data.quantity_packed
                
                # Применяем округление
                if rounding_precision:
                    calculated_qty = round(calculated_qty / rounding_precision) * rounding_precision
                elif material_unit in ['шт', 'од']:
                    calculated_qty = int(round(calculated_qty))
                else:
                    calculated_qty = round(calculated_qty, 1)
                
                calculated_materials.append({
                    'material_id': material_id,
                    'material_name': material_name,
                    'quantity': calculated_qty,
                    'unit': material_unit,
                    'material_type': material_type
                })
            
            # Использовать confirmed_materials если оператор скорректировал (брак)
            materials_to_use = calculated_materials
            if output_data.confirmed_materials:
                # TODO: здесь можно добавить логику корректировки
                pass
            
            # Проверить доступность материалов
            for material in materials_to_use:
                cursor.execute("""
                    SELECT COALESCE(quantity, 0) FROM stock_balances WHERE nomenclature_id = ?
                """, material['material_id'])
                
                balance_row = cursor.fetchone()
                balance = float(balance_row[0]) if balance_row else 0
                
                if balance < material['quantity']:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Недостатньо матеріалу '{material['material_name']}'. Доступно: {balance:.2f} {material['unit']}, Потрібно: {material['quantity']:.2f} {material['unit']}"
                    )
            
            # Создать запись выхода
            cursor.execute("""
                INSERT INTO packaging_session_outputs (
                    session_id, target_product_id, quantity_packed, 
                    calculated_materials, confirmed_materials, defect_quantity, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, session_id, output_data.target_product_id, output_data.quantity_packed,
                json.dumps(calculated_materials), 
                json.dumps(output_data.confirmed_materials) if output_data.confirmed_materials else None,
                output_data.defect_quantity, output_data.notes)
            
            output_id = int(cursor.execute("SELECT @@IDENTITY").fetchone()[0])
            
            # Списать материалы
            for material in materials_to_use:
                material_id = material['material_id']
                quantity = material['quantity']
                
                cursor.execute("""
                    SELECT COALESCE(quantity, 0) FROM stock_balances WHERE nomenclature_id = ?
                """, material_id)
                current_balance = float(cursor.fetchone()[0])
                new_balance = current_balance - quantity
                
                movement_key = f"pkg-material-{session_id}-{output_id}-{material_id}-{datetime.now().timestamp()}"
                
                cursor.execute("""
                    INSERT INTO stock_movements (
                        nomenclature_id, operation_type, quantity, balance_after,
                        source_operation_type, source_operation_id,
                        idempotency_key, operation_date, metadata
                    )
                    VALUES (?, 'withdrawal', ?, ?, 'packaging_material', ?, ?, DATEADD(HOUR, 2, GETDATE()), ?)
                """, material_id, quantity, new_balance, session.session_number, movement_key,
                    json.dumps({
                        'session_id': session_id,
                        'session_number': session.session_number,
                        'output_id': output_id,
                        'target_product_id': output_data.target_product_id
                    }))
                
                cursor.execute("""
                    UPDATE stock_balances
                    SET quantity = ?, last_updated = DATEADD(HOUR, 2, GETDATE())
                    WHERE nomenclature_id = ?
                """, new_balance, material_id)
            
            # Оприходовать готовую продукцию
            cursor.execute("""
                SELECT COALESCE(quantity, 0) FROM stock_balances 
                WHERE nomenclature_id = ?
            """, output_data.target_product_id)
            
            result = cursor.fetchone()
            target_balance = float(result[0]) if result else 0
            new_target_balance = target_balance + output_data.quantity_packed
            
            receipt_key = f"pkg-receipt-{session_id}-{output_id}-{datetime.now().timestamp()}"
            
            cursor.execute("""
                INSERT INTO stock_movements (
                    nomenclature_id, operation_type, quantity, balance_after,
                    source_operation_type, source_operation_id,
                    idempotency_key, operation_date, metadata
                )
                VALUES (?, 'receipt', ?, ?, 'packaging_output', ?, ?, DATEADD(HOUR, 2, GETDATE()), ?)
            """, output_data.target_product_id, output_data.quantity_packed, new_target_balance,
                session.session_number, receipt_key,
                json.dumps({
                    'session_id': session_id,
                    'session_number': session.session_number,
                    'output_id': output_id
                }))
            
            cursor.execute("""
                IF EXISTS (SELECT 1 FROM stock_balances WHERE nomenclature_id = ?)
                    UPDATE stock_balances
                    SET quantity = ?, last_updated = DATEADD(HOUR, 2, GETDATE())
                    WHERE nomenclature_id = ?
                ELSE
                    INSERT INTO stock_balances (nomenclature_id, quantity, last_updated)
                    VALUES (?, ?, DATEADD(HOUR, 2, GETDATE()))
            """, output_data.target_product_id, new_target_balance, output_data.target_product_id,
                output_data.target_product_id, new_target_balance)
            
            conn.commit()
            
            return {
                "message": "Вихід додано успішно",
                "output_id": output_id,
                "quantity_packed": output_data.quantity_packed,
                "materials_used": calculated_materials
            }
    
    return await run_in_threadpool(_add)


@router.post("/sessions/{session_id}/remainders")
async def add_packaging_remainder(session_id: int, remainder_data: PackagingSessionRemainderCreate):
    """
    Добавить остаток (используемые отходы) в сессию
    Например: упавшие специи, обрезки, которые можно вернуть на склад
    """
    def _add():
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Проверить сессию
            cursor.execute("SELECT status, session_number FROM packaging_sessions WHERE id = ?", session_id)
            session = cursor.fetchone()
            if not session:
                raise HTTPException(status_code=404, detail="Сесію не знайдено")
            
            if session.status == 'completed':
                raise HTTPException(status_code=400, detail="Сесія вже завершена")
            
            # Создать запись остатка
            cursor.execute("""
                INSERT INTO packaging_session_remainders (
                    session_id, nomenclature_id, weight_kg, description, notes
                )
                VALUES (?, ?, ?, ?, ?)
            """, session_id, remainder_data.nomenclature_id, remainder_data.weight_kg,
                remainder_data.description, remainder_data.notes)
            
            remainder_id = int(cursor.execute("SELECT @@IDENTITY").fetchone()[0])
            
            # Оприходовать остаток на склад
            cursor.execute("""
                SELECT COALESCE(quantity, 0) FROM stock_balances 
                WHERE nomenclature_id = ?
            """, remainder_data.nomenclature_id)
            
            result = cursor.fetchone()
            balance = float(result[0]) if result else 0
            new_balance = balance + remainder_data.weight_kg
            
            receipt_key = f"pkg-remainder-{session_id}-{remainder_id}-{datetime.now().timestamp()}"
            
            cursor.execute("""
                INSERT INTO stock_movements (
                    nomenclature_id, operation_type, quantity, balance_after,
                    source_operation_type, source_operation_id,
                    idempotency_key, operation_date, metadata
                )
                VALUES (?, 'receipt', ?, ?, 'packaging_remainder', ?, ?, DATEADD(HOUR, 2, GETDATE()), ?)
            """, remainder_data.nomenclature_id, remainder_data.weight_kg, new_balance,
                session.session_number, receipt_key,
                json.dumps({
                    'session_id': session_id,
                    'session_number': session.session_number,
                    'remainder_id': remainder_id,
                    'description': remainder_data.description
                }))
            
            cursor.execute("""
                IF EXISTS (SELECT 1 FROM stock_balances WHERE nomenclature_id = ?)
                    UPDATE stock_balances
                    SET quantity = ?, last_updated = DATEADD(HOUR, 2, GETDATE())
                    WHERE nomenclature_id = ?
                ELSE
                    INSERT INTO stock_balances (nomenclature_id, quantity, last_updated)
                    VALUES (?, ?, DATEADD(HOUR, 2, GETDATE()))
            """, remainder_data.nomenclature_id, new_balance, remainder_data.nomenclature_id,
                remainder_data.nomenclature_id, new_balance)
            
            conn.commit()
            
            return {
                "message": "Залишок додано і оприбутковано",
                "remainder_id": remainder_id,
                "weight_kg": remainder_data.weight_kg
            }
    
    return await run_in_threadpool(_add)


@router.post("/sessions/{session_id}/waste")
async def add_packaging_waste(session_id: int, waste_data: PackagingSessionWasteCreate):
    """
    Добавить отходы (списание, потери)
    Это НЕ оприходуется на склад, только фиксируется для аналитики
    """
    def _add():
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Проверить сессию
            cursor.execute("SELECT status FROM packaging_sessions WHERE id = ?", session_id)
            session = cursor.fetchone()
            if not session:
                raise HTTPException(status_code=404, detail="Сесію не знайдено")
            
            if session.status == 'completed':
                raise HTTPException(status_code=400, detail="Сесія вже завершена")
            
            # Создать запись отходов
            cursor.execute("""
                INSERT INTO packaging_session_waste (
                    session_id, waste_weight_kg, waste_description, notes
                )
                VALUES (?, ?, ?, ?)
            """, session_id, waste_data.waste_weight_kg, 
                waste_data.waste_description, waste_data.notes)
            
            waste_id = int(cursor.execute("SELECT @@IDENTITY").fetchone()[0])
            
            conn.commit()
            
            return {
                "message": "Відходи зафіксовано",
                "waste_id": waste_id,
                "waste_weight_kg": waste_data.waste_weight_kg
            }
    
    return await run_in_threadpool(_add)


@router.put("/sessions/{session_id}/complete")
async def complete_packaging_session(session_id: int, completion: PackagingSessionComplete):
    """Завершить сессию фасовки"""
    def _complete():
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Проверить сессию
            cursor.execute("SELECT status FROM packaging_sessions WHERE id = ?", session_id)
            session = cursor.fetchone()
            if not session:
                raise HTTPException(status_code=404, detail="Сесію не знайдено")
            
            if session.status == 'completed':
                raise HTTPException(status_code=400, detail="Сесія вже завершена")
            
            # Завершить сессию
            cursor.execute("""
                UPDATE packaging_sessions
                SET status = 'completed',
                    completed_at = DATEADD(HOUR, 2, GETDATE()),
                    operator_notes = COALESCE(?, operator_notes),
                    updated_at = DATEADD(HOUR, 2, GETDATE())
                WHERE id = ?
            """, completion.notes, session_id)
            
            conn.commit()
            
            return {
                "message": "Сесію фасування завершено",
                "session_id": session_id
            }
    
    return await run_in_threadpool(_complete)
