"""
Inventory API - Модуль інвентаризації складу

Функціонал:
- Створення сесій інвентаризації (повна/часткова)
- Фіксація фактичних кількостей товарів
- Автоматичний розрахунок різниць
- Коригування залишків
- Генерація звітів
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.concurrency import run_in_threadpool
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
import uuid

from database import get_db_connection
from models import (
    InventorySessionCreate, InventorySession, InventoryItemCreate,
    InventoryComplete
)

router = APIRouter(prefix="/api/inventory", tags=["inventory"])

# ============================================================================
# INVENTORY SESSIONS
# ============================================================================

@router.post("/sessions", response_model=InventorySession)
async def start_inventory_session(session_data: InventorySessionCreate):
    """
    Початок нової сесії інвентаризації

    Створює сесію та робить snapshot поточних залишків
    """
    try:
        conn = await run_in_threadpool(get_db_connection)
        cursor = conn.cursor()

        # Генеруємо номер сесії
        session_date = datetime.now().strftime("%Y%m%d")

        # Знаходимо наступний номер сесії для сьогодні
        cursor.execute("""
            SELECT MAX(CAST(RIGHT(session_number, 3) AS INT))
            FROM inventory_sessions
            WHERE session_number LIKE ?
        """, (f"INV-{session_date}-%",))

        last_num = cursor.fetchone()[0]
        next_num = (last_num or 0) + 1
        session_number = f"INV-{session_date}-{next_num:03d}"

        # Створюємо сесію
        cursor.execute("""
            INSERT INTO inventory_sessions (
                session_number, session_type, status, started_at,
                idempotency_key, metadata
            )
            VALUES (?, ?, 'in_progress', DATEADD(HOUR, 2, GETDATE()), ?, ?)
        """, (
            session_number,
            session_data.session_type,
            session_data.idempotency_key,
            str(session_data.metadata) if session_data.metadata else None
        ))

        session_id = cursor.execute("SELECT @@IDENTITY").fetchone()[0]

        # Створюємо snapshot поточних залишків для всієї номенклатури
        if session_data.session_type == "full":
            cursor.execute("""
                INSERT INTO inventory_snapshot (
                    session_id, nomenclature_id, snapshot_quantity, snapshot_at
                )
                SELECT
                    ?,
                    n.id,
                    COALESCE(sb.quantity, 0),
                    DATEADD(HOUR, 2, GETDATE())
                FROM nomenclature n
                LEFT JOIN stock_balances sb ON sb.nomenclature_id = n.id
                WHERE n.is_active = 1
            """, (session_id,))

            # Створюємо записи для inventory_items
            cursor.execute("""
                INSERT INTO inventory_items (
                    session_id, nomenclature_id, system_quantity,
                    status, requires_verification
                )
                SELECT
                    ?,
                    nomenclature_id,
                    snapshot_quantity,
                    'pending',
                    0
                FROM inventory_snapshot
                WHERE session_id = ?
            """, (session_id, session_id))

        conn.commit()

        # Отримуємо створену сесію
        cursor.execute("""
            SELECT id, session_number, session_type, status, started_at,
                   completed_at, idempotency_key, metadata
            FROM inventory_sessions
            WHERE id = ?
        """, (session_id,))

        row = cursor.fetchone()
        cursor.close()
        conn.close()

        return {
            "id": row[0],
            "session_type": row[2],
            "status": row[3],
            "started_at": row[4],
            "completed_at": row[5],
            "idempotency_key": row[6],
            "metadata": row[7]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Помилка створення сесії: {str(e)}")


@router.get("/sessions/{session_id}", response_model=InventorySession)
async def get_inventory_session(session_id: int):
    """Отримати інформацію про сесію інвентаризації"""
    try:
        conn = await run_in_threadpool(get_db_connection)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, session_number, session_type, status, started_at,
                   completed_at, idempotency_key, metadata
            FROM inventory_sessions
            WHERE id = ?
        """, (session_id,))

        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail="Сесію не знайдено")

        return {
            "id": row[0],
            "session_type": row[2],
            "status": row[3],
            "started_at": row[4],
            "completed_at": row[5],
            "idempotency_key": row[6],
            "metadata": row[7]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/items")
async def get_inventory_items(session_id: int):
    """Отримати всі позиції інвентаризації"""
    try:
        conn = await run_in_threadpool(get_db_connection)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                ii.id,
                ii.nomenclature_id,
                n.name as nomenclature_name,
                n.category,
                n.unit,
                ii.system_quantity,
                ii.actual_quantity,
                ii.difference,
                ii.difference_percent,
                ii.status,
                ii.requires_verification,
                ii.counted_at,
                ii.notes
            FROM inventory_items ii
            JOIN nomenclature n ON n.id = ii.nomenclature_id
            WHERE ii.session_id = ?
            ORDER BY n.name
        """, (session_id,))

        items = []
        for row in cursor.fetchall():
            items.append({
                "id": row[0],
                "nomenclature_id": row[1],
                "nomenclature_name": row[2],
                "category": row[3],
                "unit": row[4],
                "system_quantity": float(row[5]) if row[5] else 0,
                "actual_quantity": float(row[6]) if row[6] else None,
                "difference": float(row[7]) if row[7] else None,
                "difference_percent": float(row[8]) if row[8] else None,
                "status": row[9],
                "requires_verification": bool(row[10]),
                "counted_at": row[11],
                "notes": row[12]
            })

        cursor.close()
        conn.close()

        return items

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/complete")
async def complete_inventory(session_id: int, complete_data: InventoryComplete):
    """
    Завершення інвентаризації та коригування залишків

    Процес:
    1. Перевірка що всі позиції підраховані
    2. Розрахунок різниць
    3. Створення коригувальних проводок
    4. Оновлення залишків
    5. Закриття сесії
    """
    try:
        conn = await run_in_threadpool(get_db_connection)
        cursor = conn.cursor()

        # Перевіряємо чи сесія існує і не закрита
        cursor.execute("""
            SELECT status FROM inventory_sessions WHERE id = ?
        """, (session_id,))

        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Сесію не знайдено")

        if row[0] != 'in_progress':
            raise HTTPException(
                status_code=400,
                detail=f"Сесія вже завершена. Статус: {row[0]}"
            )

        adjustments_count = 0

        # Обробляємо кожну позицію
        for item in complete_data.items:
            # Отримуємо системну кількість зі snapshot
            cursor.execute("""
                SELECT snapshot_quantity
                FROM inventory_snapshot
                WHERE session_id = ? AND nomenclature_id = ?
            """, (session_id, item.nomenclature_id))

            snapshot_row = cursor.fetchone()
            if not snapshot_row:
                # Якщо це часткова інвентаризація, створюємо snapshot
                cursor.execute("""
                    SELECT COALESCE(quantity, 0)
                    FROM stock_balances
                    WHERE nomenclature_id = ?
                """, (item.nomenclature_id,))

                balance_row = cursor.fetchone()
                system_qty = float(balance_row[0]) if balance_row else 0

                # Створюємо snapshot
                cursor.execute("""
                    INSERT INTO inventory_snapshot (
                        session_id, nomenclature_id, snapshot_quantity, snapshot_at
                    )
                    VALUES (?, ?, ?, DATEADD(HOUR, 2, GETDATE()))
                """, (session_id, item.nomenclature_id, system_qty))
            else:
                system_qty = float(snapshot_row[0])

            actual_qty = float(item.actual_quantity)
            difference = actual_qty - system_qty
            difference_percent = (difference / system_qty * 100) if system_qty != 0 else 0

            requires_verification = abs(difference_percent) > 10

            # Оновлюємо або створюємо запис в inventory_items
            cursor.execute("""
                IF EXISTS (SELECT 1 FROM inventory_items WHERE session_id = ? AND nomenclature_id = ?)
                BEGIN
                    UPDATE inventory_items
                    SET actual_quantity = ?,
                        difference = ?,
                        difference_percent = ?,
                        status = CASE
                            WHEN ABS(?) > 0.001 THEN 'discrepancy'
                            ELSE 'verified'
                        END,
                        requires_verification = ?,
                        counted_at = DATEADD(HOUR, 2, GETDATE())
                    WHERE session_id = ? AND nomenclature_id = ?
                END
                ELSE
                BEGIN
                    INSERT INTO inventory_items (
                        session_id, nomenclature_id, system_quantity,
                        actual_quantity, difference, difference_percent,
                        status, requires_verification, counted_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?,
                        CASE WHEN ABS(?) > 0.001 THEN 'discrepancy' ELSE 'verified' END,
                        ?, DATEADD(HOUR, 2, GETDATE()))
                END
            """, (
                session_id, item.nomenclature_id,
                actual_qty, difference, difference_percent,
                difference,
                1 if requires_verification else 0,
                session_id, item.nomenclature_id,
                # Insert params
                session_id, item.nomenclature_id, system_qty,
                actual_qty, difference, difference_percent,
                difference,
                1 if requires_verification else 0
            ))

            # Якщо є різниця, створюємо коригувальну проводку
            if abs(difference) > 0.001:
                adjustments_count += 1

                # Створюємо movement
                idempotency_key = f"{complete_data.idempotency_key}-{item.nomenclature_id}"
                operation_type = "inventory_adjustment"

                # Оновлюємо баланс з блокуванням
                cursor.execute("""
                    UPDATE stock_balances WITH (UPDLOCK, ROWLOCK)
                    SET quantity = ?
                    WHERE nomenclature_id = ?
                """, (actual_qty, item.nomenclature_id))

                # Якщо запису не було, створюємо
                if cursor.rowcount == 0:
                    cursor.execute("""
                        INSERT INTO stock_balances (nomenclature_id, quantity, last_updated)
                        VALUES (?, ?, DATEADD(HOUR, 2, GETDATE()))
                    """, (item.nomenclature_id, actual_qty))

                # Записуємо в stock_movements
                metadata_json = f'{{"session_id": {session_id}, "difference": {difference}}}'

                cursor.execute("""
                    INSERT INTO stock_movements (
                        nomenclature_id, operation_type, quantity,
                        balance_after, idempotency_key, metadata,
                        operation_date, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?,
                        DATEADD(HOUR, 2, GETDATE()),
                        DATEADD(HOUR, 2, GETDATE()))
                """, (
                    item.nomenclature_id,
                    operation_type,
                    difference,  # може бути + або -
                    actual_qty,
                    idempotency_key,
                    metadata_json
                ))

        # Закриваємо сесію
        cursor.execute("""
            UPDATE inventory_sessions
            SET status = 'completed',
                completed_at = DATEADD(HOUR, 2, GETDATE())
            WHERE id = ?
        """, (session_id,))

        conn.commit()
        cursor.close()
        conn.close()

        return {
            "session_id": session_id,
            "status": "completed",
            "adjustments_count": adjustments_count,
            "message": "Інвентаризацію успішно завершено"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Помилка завершення інвентаризації: {str(e)}")


@router.get("/sessions")
async def list_inventory_sessions(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None
):
    """Список всіх сесій інвентаризації"""
    try:
        conn = await run_in_threadpool(get_db_connection)
        cursor = conn.cursor()

        where_clause = ""
        params = []

        if status:
            where_clause = "WHERE status = ?"
            params.append(status)

        query = f"""
            SELECT
                id, session_number, session_type, status,
                started_at, completed_at, idempotency_key
            FROM inventory_sessions
            {where_clause}
            ORDER BY started_at DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """

        params.extend([offset, limit])
        cursor.execute(query, params)

        sessions = []
        for row in cursor.fetchall():
            sessions.append({
                "id": row[0],
                "session_number": row[1],
                "session_type": row[2],
                "status": row[3],
                "started_at": row[4],
                "completed_at": row[5],
                "idempotency_key": row[6]
            })

        cursor.close()
        conn.close()

        return sessions

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
