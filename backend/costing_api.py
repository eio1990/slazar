"""
Costing API - Модуль калькуляції собівартості

Функціонал:
- Розрахунок собівартості операцій розділки (з урахуванням СТЕКА)
- Калькуляція собівартості виробничих партій
- Калькуляція собівартості фасування
- Оновлення середньозваженої вартості номенклатури
"""

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from typing import Optional
from decimal import Decimal
from datetime import datetime

from database import get_db_connection
from models import (
    ButcheryOperationCost, BatchCost, PackagingBatchCost,
    NomenclatureCost, NomenclatureCostUpdate
)

router = APIRouter(prefix="/api/costing", tags=["costing"])


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_nomenclature_cost(cursor, nomenclature_id: int) -> float:
    """
    Отримати поточну середньозважену собівартість номенклатури

    Якщо собівартість не встановлена, повертає 0
    """
    cursor.execute("""
        SELECT weighted_avg_cost
        FROM nomenclature_costs
        WHERE nomenclature_id = ?
    """, (nomenclature_id,))

    row = cursor.fetchone()
    return float(row[0]) if row else 0.0


def update_nomenclature_cost(cursor, nomenclature_id: int, quantity: float, unit_cost: float):
    """
    Оновити середньозважену собівартість номенклатури

    Формула: new_avg = (old_balance × old_avg + new_qty × new_cost) / (old_balance + new_qty)
    """
    # Отримати поточний баланс
    cursor.execute("""
        SELECT COALESCE(quantity, 0)
        FROM stock_balances
        WHERE nomenclature_id = ?
    """, (nomenclature_id,))

    balance_row = cursor.fetchone()
    current_balance = float(balance_row[0]) if balance_row else 0.0

    # Отримати поточну собівартість
    cursor.execute("""
        SELECT weighted_avg_cost, total_quantity, total_value
        FROM nomenclature_costs
        WHERE nomenclature_id = ?
    """, (nomenclature_id,))

    cost_row = cursor.fetchone()

    if cost_row:
        old_avg = float(cost_row[0])
        old_total_qty = float(cost_row[1])
        old_total_value = float(cost_row[2])
    else:
        old_avg = 0.0
        old_total_qty = 0.0
        old_total_value = 0.0

    # Розрахувати нову середньозважену
    new_total_qty = old_total_qty + quantity
    new_total_value = old_total_value + (quantity * unit_cost)

    if new_total_qty > 0:
        new_avg = new_total_value / new_total_qty
    else:
        new_avg = unit_cost

    # Оновити або створити запис
    cursor.execute("""
        IF EXISTS (SELECT 1 FROM nomenclature_costs WHERE nomenclature_id = ?)
        BEGIN
            UPDATE nomenclature_costs
            SET weighted_avg_cost = ?,
                last_purchase_cost = ?,
                total_quantity = ?,
                total_value = ?,
                last_updated = DATEADD(HOUR, 2, GETDATE())
            WHERE nomenclature_id = ?
        END
        ELSE
        BEGIN
            INSERT INTO nomenclature_costs (
                nomenclature_id, weighted_avg_cost, last_purchase_cost,
                total_quantity, total_value, last_updated
            )
            VALUES (?, ?, ?, ?, ?, DATEADD(HOUR, 2, GETDATE()))
        END
    """, (
        nomenclature_id, new_avg, unit_cost, new_total_qty, new_total_value, nomenclature_id,
        nomenclature_id, new_avg, unit_cost, new_total_qty, new_total_value
    ))


# ============================================================================
# BUTCHERY COSTING (з урахуванням СТЕКА)
# ============================================================================

@router.post("/calculate-butchery/{operation_id}", response_model=ButcheryOperationCost)
async def calculate_butchery_cost(operation_id: int):
    """
    Розрахувати собівартість операції розділки з урахуванням СТЕКА

    СТЕК = різниця між вхідною вагою і сумою всіх виходів (включаючи liquid-waste)
    Ця різниця розподіляється на собівартість полуфабрикатів
    """
    try:
        conn = await run_in_threadpool(get_db_connection)
        cursor = conn.cursor()

        # Отримати дані операції розділки
        cursor.execute("""
            SELECT
                bo.recipe_id,
                bo.input_weight,
                br.input_nomenclature_id
            FROM butchery_operations bo
            JOIN butchery_recipes br ON br.id = bo.recipe_id
            WHERE bo.id = ?
        """, (operation_id,))

        operation_row = cursor.fetchone()
        if not operation_row:
            raise HTTPException(status_code=404, detail="Операцію розділки не знайдено")

        recipe_id = operation_row[0]
        input_weight = float(operation_row[1])
        input_nomenclature_id = operation_row[2]

        # Отримати собівартість вхідної сировини
        input_cost_per_kg = get_nomenclature_cost(cursor, input_nomenclature_id)
        input_total_cost = input_weight * input_cost_per_kg

        # Отримати всі виходи операції
        cursor.execute("""
            SELECT
                boo.output_nomenclature_id,
                boo.actual_weight,
                n.nomenclature_type
            FROM butchery_operation_outputs boo
            JOIN nomenclature n ON n.id = boo.output_nomenclature_id
            WHERE boo.operation_id = ?
        """, (operation_id,))

        outputs = cursor.fetchall()

        # Розділити на полуфабрикати і відходи/стек
        total_output_weight = 0.0
        semifinished_weight = 0.0
        waste_weight = 0.0

        semifinished_outputs = []

        for output in outputs:
            output_id = output[0]
            weight = float(output[1])
            nomenclature_type = output[2]

            total_output_weight += weight

            if nomenclature_type == 'liquid-waste':
                # Це стек (кров і вода)
                waste_weight += weight
            elif nomenclature_type in ['semi-finished', 'raw']:
                # Це полуфабрикат
                semifinished_weight += weight
                semifinished_outputs.append({
                    'nomenclature_id': output_id,
                    'weight': weight
                })
            else:
                # Інші відходи
                waste_weight += weight

        # Розрахувати стек (усушку)
        shrinkage_weight = input_weight - total_output_weight
        shrinkage_percent = (shrinkage_weight / input_weight * 100) if input_weight > 0 else 0.0

        # Розрахувати скориговану собівартість
        # Якщо є стек, вартість сировини розподіляється на менший вихід
        if total_output_weight > 0:
            adjusted_cost_per_kg = input_total_cost / total_output_weight
        else:
            adjusted_cost_per_kg = input_cost_per_kg

        # Зберегти калькуляцію в БД
        cursor.execute("""
            IF EXISTS (SELECT 1 FROM butchery_operation_costs WHERE operation_id = ?)
            BEGIN
                UPDATE butchery_operation_costs
                SET input_nomenclature_id = ?,
                    input_weight = ?,
                    input_cost_per_kg = ?,
                    input_total_cost = ?,
                    total_output_weight = ?,
                    semifinished_weight = ?,
                    waste_weight = ?,
                    shrinkage_weight = ?,
                    shrinkage_percent = ?,
                    adjusted_cost_per_kg = ?,
                    calculated_at = DATEADD(HOUR, 2, GETDATE())
                WHERE operation_id = ?
            END
            ELSE
            BEGIN
                INSERT INTO butchery_operation_costs (
                    operation_id, input_nomenclature_id, input_weight,
                    input_cost_per_kg, input_total_cost, total_output_weight,
                    semifinished_weight, waste_weight, shrinkage_weight,
                    shrinkage_percent, adjusted_cost_per_kg, calculated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, DATEADD(HOUR, 2, GETDATE()))
            END
        """, (
            operation_id, input_nomenclature_id, input_weight, input_cost_per_kg,
            input_total_cost, total_output_weight, semifinished_weight, waste_weight,
            shrinkage_weight, shrinkage_percent, adjusted_cost_per_kg, operation_id,
            # Insert params
            operation_id, input_nomenclature_id, input_weight, input_cost_per_kg,
            input_total_cost, total_output_weight, semifinished_weight, waste_weight,
            shrinkage_weight, shrinkage_percent, adjusted_cost_per_kg
        ))

        # Оновити середньозважену собівартість кожного полуфабрикату
        for output in semifinished_outputs:
            update_nomenclature_cost(
                cursor,
                output['nomenclature_id'],
                output['weight'],
                adjusted_cost_per_kg
            )

        conn.commit()

        # Отримати ID записа
        cursor.execute("""
            SELECT id FROM butchery_operation_costs WHERE operation_id = ?
        """, (operation_id,))
        cost_id = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        return ButcheryOperationCost(
            id=cost_id,
            operation_id=operation_id,
            input_nomenclature_id=input_nomenclature_id,
            input_weight=input_weight,
            input_cost_per_kg=input_cost_per_kg,
            input_total_cost=input_total_cost,
            total_output_weight=total_output_weight,
            semifinished_weight=semifinished_weight,
            waste_weight=waste_weight,
            shrinkage_weight=shrinkage_weight,
            shrinkage_percent=shrinkage_percent,
            adjusted_cost_per_kg=adjusted_cost_per_kg,
            calculated_at=datetime.now()
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Помилка розрахунку собівартості розділки: {str(e)}"
        )


@router.get("/butchery/{operation_id}", response_model=ButcheryOperationCost)
async def get_butchery_cost(operation_id: int):
    """Отримати збережену калькуляцію операції розділки"""
    try:
        conn = await run_in_threadpool(get_db_connection)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id, operation_id, input_nomenclature_id, input_weight,
                input_cost_per_kg, input_total_cost, total_output_weight,
                semifinished_weight, waste_weight, shrinkage_weight,
                shrinkage_percent, adjusted_cost_per_kg, calculated_at
            FROM butchery_operation_costs
            WHERE operation_id = ?
        """, (operation_id,))

        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail="Калькуляцію не знайдено")

        return ButcheryOperationCost(
            id=row[0],
            operation_id=row[1],
            input_nomenclature_id=row[2],
            input_weight=float(row[3]),
            input_cost_per_kg=float(row[4]),
            input_total_cost=float(row[5]),
            total_output_weight=float(row[6]),
            semifinished_weight=float(row[7]),
            waste_weight=float(row[8]),
            shrinkage_weight=float(row[9]),
            shrinkage_percent=float(row[10]),
            adjusted_cost_per_kg=float(row[11]),
            calculated_at=row[12]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# NOMENCLATURE COSTS
# ============================================================================

@router.get("/nomenclature/{nomenclature_id}", response_model=NomenclatureCost)
async def get_nomenclature_cost_info(nomenclature_id: int):
    """Отримати інформацію про собівартість номенклатури"""
    try:
        conn = await run_in_threadpool(get_db_connection)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                nomenclature_id, weighted_avg_cost, last_purchase_cost,
                total_quantity, total_value, last_updated
            FROM nomenclature_costs
            WHERE nomenclature_id = ?
        """, (nomenclature_id,))

        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail="Собівартість не знайдено")

        return NomenclatureCost(
            nomenclature_id=row[0],
            weighted_avg_cost=float(row[1]),
            last_purchase_cost=float(row[2]) if row[2] else None,
            total_quantity=float(row[3]),
            total_value=float(row[4]),
            last_updated=row[5]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/nomenclature/update-cost")
async def update_nomenclature_cost_endpoint(cost_update: NomenclatureCostUpdate):
    """
    Оновити собівартість номенклатури (при приході товару)

    Використовується при ручному приході товару на склад
    """
    try:
        conn = await run_in_threadpool(get_db_connection)
        cursor = conn.cursor()

        update_nomenclature_cost(
            cursor,
            cost_update.nomenclature_id,
            cost_update.quantity,
            cost_update.purchase_cost
        )

        conn.commit()
        cursor.close()
        conn.close()

        return {
            "status": "success",
            "message": "Собівартість оновлено",
            "nomenclature_id": cost_update.nomenclature_id
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Помилка оновлення собівартості: {str(e)}"
        )
