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


# ============================================================================
# PRODUCTION BATCH COSTING
# ============================================================================

@router.post("/calculate-batch/{batch_id}", response_model=BatchCost)
async def calculate_batch_cost(batch_id: int):
    """
    Розрахувати собівартість виробничої партії

    Враховує:
    - Сировину (на основі середньозваженої вартості)
    - Сіль та воду
    - Спеції (включаючи суміш зі складу)
    - Оболонки
    - Інші матеріали
    - Усушку (втрати ваги при виробництві)
    """
    try:
        conn = await run_in_threadpool(get_db_connection)
        cursor = conn.cursor()

        # Отримати інформацію про партію
        cursor.execute("""
            SELECT
                b.recipe_id,
                b.initial_weight,
                b.final_weight,
                b.status
            FROM batches b
            WHERE b.id = ?
        """, (batch_id,))

        batch_row = cursor.fetchone()
        if not batch_row:
            raise HTTPException(status_code=404, detail="Партію не знайдено")

        recipe_id = batch_row[0]
        initial_weight = float(batch_row[1]) if batch_row[1] else 0.0
        final_weight = float(batch_row[2]) if batch_row[2] else 0.0
        status = batch_row[3]

        # Ініціалізація змінних собівартості
        raw_materials_cost = 0.0
        salt_cost = 0.0
        spices_cost = 0.0
        casings_cost = 0.0
        other_materials_cost = 0.0

        # 1. Розрахувати вартість сировини
        cursor.execute("""
            SELECT
                bm.nomenclature_id,
                bm.quantity_used,
                n.category
            FROM batch_materials bm
            JOIN nomenclature n ON n.id = bm.nomenclature_id
            WHERE bm.batch_id = ? AND bm.material_type = 'raw'
        """, (batch_id,))

        for row in cursor.fetchall():
            nomenclature_id = row[0]
            quantity = float(row[1])
            category = row[2]

            cost_per_unit = get_nomenclature_cost(cursor, nomenclature_id)
            material_cost = quantity * cost_per_unit
            raw_materials_cost += material_cost

        # 2. Розрахувати вартість солі
        cursor.execute("""
            SELECT
                bm.nomenclature_id,
                bm.quantity_used
            FROM batch_materials bm
            JOIN nomenclature n ON n.id = bm.nomenclature_id
            WHERE bm.batch_id = ? AND n.name LIKE '%сіль%'
        """, (batch_id,))

        for row in cursor.fetchall():
            nomenclature_id = row[0]
            quantity = float(row[1])

            cost_per_unit = get_nomenclature_cost(cursor, nomenclature_id)
            salt_cost += quantity * cost_per_unit

        # 3. Розрахувати вартість спецій (включаючи суміш зі складу)
        cursor.execute("""
            SELECT
                bm.nomenclature_id,
                bm.quantity_used,
                n.category
            FROM batch_materials bm
            JOIN nomenclature n ON n.id = bm.nomenclature_id
            WHERE bm.batch_id = ?
                AND (n.category = 'spice' OR n.name LIKE '%суміш%')
                AND n.name NOT LIKE '%сіль%'
        """, (batch_id,))

        for row in cursor.fetchall():
            nomenclature_id = row[0]
            quantity = float(row[1])

            cost_per_unit = get_nomenclature_cost(cursor, nomenclature_id)
            spices_cost += quantity * cost_per_unit

        # 4. Розрахувати вартість оболонок
        cursor.execute("""
            SELECT
                bm.nomenclature_id,
                bm.quantity_used
            FROM batch_materials bm
            JOIN nomenclature n ON n.id = bm.nomenclature_id
            WHERE bm.batch_id = ?
                AND (n.name LIKE '%оболон%' OR n.category = 'casing')
        """, (batch_id,))

        for row in cursor.fetchall():
            nomenclature_id = row[0]
            quantity = float(row[1])

            cost_per_unit = get_nomenclature_cost(cursor, nomenclature_id)
            casings_cost += quantity * cost_per_unit

        # 5. Інші матеріали (нитки, крючки, тощо)
        cursor.execute("""
            SELECT
                bm.nomenclature_id,
                bm.quantity_used,
                n.category
            FROM batch_materials bm
            JOIN nomenclature n ON n.id = bm.nomenclature_id
            WHERE bm.batch_id = ?
                AND bm.material_type = 'material'
                AND n.category NOT IN ('spice', 'casing')
                AND n.name NOT LIKE '%оболон%'
                AND n.name NOT LIKE '%сіль%'
                AND n.name NOT LIKE '%суміш%'
        """, (batch_id,))

        for row in cursor.fetchall():
            nomenclature_id = row[0]
            quantity = float(row[1])

            cost_per_unit = get_nomenclature_cost(cursor, nomenclature_id)
            other_materials_cost += quantity * cost_per_unit

        # Загальна собівартість
        total_cost = (
            raw_materials_cost + salt_cost + spices_cost +
            casings_cost + other_materials_cost
        )

        # Собівартість за кг
        if final_weight > 0:
            cost_per_kg = total_cost / final_weight
        else:
            cost_per_kg = 0.0

        # Розрахувати усушку
        shrinkage_weight = initial_weight - final_weight
        shrinkage_percent = (shrinkage_weight / initial_weight * 100) if initial_weight > 0 else 0.0

        # Зберегти калькуляцію
        cursor.execute("""
            IF EXISTS (SELECT 1 FROM batch_costs WHERE batch_id = ?)
            BEGIN
                UPDATE batch_costs
                SET raw_materials_cost = ?,
                    salt_cost = ?,
                    spices_cost = ?,
                    casings_cost = ?,
                    other_materials_cost = ?,
                    total_cost = ?,
                    final_weight = ?,
                    cost_per_kg = ?,
                    shrinkage_weight = ?,
                    shrinkage_percent = ?,
                    updated_at = DATEADD(HOUR, 2, GETDATE())
                WHERE batch_id = ?
            END
            ELSE
            BEGIN
                INSERT INTO batch_costs (
                    batch_id, raw_materials_cost, salt_cost, spices_cost,
                    casings_cost, other_materials_cost, total_cost,
                    final_weight, cost_per_kg, shrinkage_weight, shrinkage_percent,
                    calculated_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    DATEADD(HOUR, 2, GETDATE()), DATEADD(HOUR, 2, GETDATE()))
            END
        """, (
            batch_id, raw_materials_cost, salt_cost, spices_cost, casings_cost,
            other_materials_cost, total_cost, final_weight, cost_per_kg,
            shrinkage_weight, shrinkage_percent, batch_id,
            # Insert params
            batch_id, raw_materials_cost, salt_cost, spices_cost, casings_cost,
            other_materials_cost, total_cost, final_weight, cost_per_kg,
            shrinkage_weight, shrinkage_percent
        ))

        # Оновити собівартість готової продукції
        cursor.execute("""
            SELECT target_product_id FROM recipes WHERE id = ?
        """, (recipe_id,))

        product_row = cursor.fetchone()
        if product_row and final_weight > 0:
            product_id = product_row[0]
            update_nomenclature_cost(cursor, product_id, final_weight, cost_per_kg)

        conn.commit()
        cursor.close()
        conn.close()

        return BatchCost(
            batch_id=batch_id,
            raw_materials_cost=raw_materials_cost,
            salt_cost=salt_cost,
            spices_cost=spices_cost,
            casings_cost=casings_cost,
            other_materials_cost=other_materials_cost,
            total_cost=total_cost,
            final_weight=final_weight,
            cost_per_kg=cost_per_kg,
            shrinkage_weight=shrinkage_weight,
            shrinkage_percent=shrinkage_percent,
            calculated_at=datetime.now(),
            updated_at=datetime.now()
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Помилка розрахунку собівартості партії: {str(e)}"
        )


@router.get("/batch/{batch_id}", response_model=BatchCost)
async def get_batch_cost(batch_id: int):
    """Отримати збережену калькуляцію виробничої партії"""
    try:
        conn = await run_in_threadpool(get_db_connection)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                batch_id, raw_materials_cost, salt_cost, spices_cost,
                casings_cost, other_materials_cost, total_cost,
                final_weight, cost_per_kg, shrinkage_weight, shrinkage_percent,
                calculated_at, updated_at
            FROM batch_costs
            WHERE batch_id = ?
        """, (batch_id,))

        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail="Калькуляцію не знайдено")

        return BatchCost(
            batch_id=row[0],
            raw_materials_cost=float(row[1]),
            salt_cost=float(row[2]),
            spices_cost=float(row[3]),
            casings_cost=float(row[4]),
            other_materials_cost=float(row[5]),
            total_cost=float(row[6]),
            final_weight=float(row[7]),
            cost_per_kg=float(row[8]),
            shrinkage_weight=float(row[9]),
            shrinkage_percent=float(row[10]),
            calculated_at=row[11],
            updated_at=row[12]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PACKAGING BATCH COSTING
# ============================================================================

@router.post("/calculate-packaging/{packaging_batch_id}", response_model=PackagingBatchCost)
async def calculate_packaging_cost(packaging_batch_id: int):
    """
    Розрахувати собівартість партії фасування

    Враховує:
    - Вартість вагової продукції (source product)
    - Пакувальні матеріали (пакети, лотки, етикетки, плівка)
    - Брак та втрати (waste)
    """
    try:
        conn = await run_in_threadpool(get_db_connection)
        cursor = conn.cursor()

        # Отримати інформацію про партію фасування
        cursor.execute("""
            SELECT
                pb.source_product_id,
                pb.source_weight_taken,
                pb.actual_packed_quantity,
                pb.waste_quantity,
                pb.status
            FROM packaging_batches pb
            WHERE pb.id = ?
        """, (packaging_batch_id,))

        batch_row = cursor.fetchone()
        if not batch_row:
            raise HTTPException(status_code=404, detail="Партію фасування не знайдено")

        source_product_id = batch_row[0]
        source_weight = float(batch_row[1])
        packed_quantity = int(batch_row[2])
        waste_quantity = float(batch_row[3])

        # 1. Вартість вагової продукції
        source_cost_per_kg = get_nomenclature_cost(cursor, source_product_id)
        source_product_total = source_weight * source_cost_per_kg

        # 2. Вартість пакувальних матеріалів
        packaging_materials_cost = 0.0

        cursor.execute("""
            SELECT
                pmc.material_id,
                pmc.quantity_used
            FROM packaging_material_consumption pmc
            JOIN packaging_operations po ON po.id = pmc.operation_id
            WHERE po.batch_id = ?
        """, (packaging_batch_id,))

        for row in cursor.fetchall():
            material_id = row[0]
            quantity = float(row[1])

            cost_per_unit = get_nomenclature_cost(cursor, material_id)
            packaging_materials_cost += quantity * cost_per_unit

        # Загальна собівартість
        total_cost = source_product_total + packaging_materials_cost

        # Вартість відходів
        waste_cost = waste_quantity * source_cost_per_kg

        # Собівартість за одиницю
        if packed_quantity > 0:
            cost_per_unit = total_cost / packed_quantity
        else:
            cost_per_unit = 0.0

        # Зберегти калькуляцію
        cursor.execute("""
            IF EXISTS (SELECT 1 FROM packaging_batch_costs WHERE packaging_batch_id = ?)
            BEGIN
                UPDATE packaging_batch_costs
                SET source_product_cost = ?,
                    source_product_total = ?,
                    packaging_materials_cost = ?,
                    total_cost = ?,
                    packed_quantity = ?,
                    cost_per_unit = ?,
                    waste_weight = ?,
                    waste_cost = ?,
                    updated_at = DATEADD(HOUR, 2, GETDATE())
                WHERE packaging_batch_id = ?
            END
            ELSE
            BEGIN
                INSERT INTO packaging_batch_costs (
                    packaging_batch_id, source_product_cost, source_product_total,
                    packaging_materials_cost, total_cost, packed_quantity,
                    cost_per_unit, waste_weight, waste_cost,
                    calculated_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?,
                    DATEADD(HOUR, 2, GETDATE()), DATEADD(HOUR, 2, GETDATE()))
            END
        """, (
            packaging_batch_id, source_cost_per_kg, source_product_total,
            packaging_materials_cost, total_cost, packed_quantity,
            cost_per_unit, waste_quantity, waste_cost, packaging_batch_id,
            # Insert params
            packaging_batch_id, source_cost_per_kg, source_product_total,
            packaging_materials_cost, total_cost, packed_quantity,
            cost_per_unit, waste_quantity, waste_cost
        ))

        # Оновити собівартість SKU
        cursor.execute("""
            SELECT target_product_id FROM packaging_batches WHERE id = ?
        """, (packaging_batch_id,))

        target_row = cursor.fetchone()
        if target_row and packed_quantity > 0:
            target_product_id = target_row[0]
            update_nomenclature_cost(cursor, target_product_id, packed_quantity, cost_per_unit)

        conn.commit()
        cursor.close()
        conn.close()

        return PackagingBatchCost(
            packaging_batch_id=packaging_batch_id,
            source_product_cost=source_cost_per_kg,
            source_product_total=source_product_total,
            packaging_materials_cost=packaging_materials_cost,
            total_cost=total_cost,
            packed_quantity=packed_quantity,
            cost_per_unit=cost_per_unit,
            waste_weight=waste_quantity,
            waste_cost=waste_cost,
            calculated_at=datetime.now(),
            updated_at=datetime.now()
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Помилка розрахунку собівартості фасування: {str(e)}"
        )


@router.get("/packaging/{packaging_batch_id}", response_model=PackagingBatchCost)
async def get_packaging_cost(packaging_batch_id: int):
    """Отримати збережену калькуляцію партії фасування"""
    try:
        conn = await run_in_threadpool(get_db_connection)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                packaging_batch_id, source_product_cost, source_product_total,
                packaging_materials_cost, total_cost, packed_quantity,
                cost_per_unit, waste_weight, waste_cost,
                calculated_at, updated_at
            FROM packaging_batch_costs
            WHERE packaging_batch_id = ?
        """, (packaging_batch_id,))

        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail="Калькуляцію не знайдено")

        return PackagingBatchCost(
            packaging_batch_id=row[0],
            source_product_cost=float(row[1]),
            source_product_total=float(row[2]),
            packaging_materials_cost=float(row[3]),
            total_cost=float(row[4]),
            packed_quantity=int(row[5]),
            cost_per_unit=float(row[6]),
            waste_weight=float(row[7]),
            waste_cost=float(row[8]),
            calculated_at=row[9],
            updated_at=row[10]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
