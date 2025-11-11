from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from typing import List, Optional
from datetime import datetime
import json
import os
import io
import csv
from dotenv import load_dotenv

from database import get_db_connection, init_database
from models import (
    NomenclatureCreate, Nomenclature, StockOperation,
    StockMovement, StockBalance, InventorySessionCreate,
    InventorySession, InventoryComplete, SyncBatch
)

load_dotenv()

app = FastAPI(title="Склад API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    try:
        await run_in_threadpool(init_database)
    except Exception as e:
        print(f"Error initializing database: {e}")

# Helper functions
def round_quantity(quantity: float, precision: int) -> float:
    """Round quantity based on precision"""
    if precision == 0:
        return float(int(round(quantity)))
    return round(quantity, precision)

def get_nomenclature_precision(conn, nomenclature_id: int) -> int:
    """Get precision for nomenclature"""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT precision_digits FROM nomenclature WHERE id = ?",
        (nomenclature_id,)
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Номенклатура не знайдена")
    return row[0]

def get_current_balance_locked(conn, nomenclature_id: int) -> float:
    """Get current balance with row lock (FOR UPDATE equivalent in MS SQL)"""
    cursor = conn.cursor()
    # WITH (UPDLOCK, ROWLOCK) provides row-level exclusive lock
    cursor.execute(
        """SELECT quantity FROM stock_balances WITH (UPDLOCK, ROWLOCK) 
           WHERE nomenclature_id = ?""",
        (nomenclature_id,)
    )
    row = cursor.fetchone()
    return float(row[0]) if row else 0.0

def update_balance(conn, nomenclature_id: int, new_balance: float):
    """Update or insert balance"""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT nomenclature_id FROM stock_balances WHERE nomenclature_id = ?",
        (nomenclature_id,)
    )
    if cursor.fetchone():
        cursor.execute(
            "UPDATE stock_balances SET quantity = ?, last_updated = GETDATE() WHERE nomenclature_id = ?",
            (new_balance, nomenclature_id)
        )
    else:
        cursor.execute(
            "INSERT INTO stock_balances (nomenclature_id, quantity) VALUES (?, ?)",
            (nomenclature_id, new_balance)
        )

# API Endpoints

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "warehouse-api"}

@app.get("/api/nomenclature", response_model=List[Nomenclature])
async def get_nomenclature():
    """Отримати всю номенклатуру"""
    def _get():
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name, category, unit, precision_digits, created_at, updated_at FROM nomenclature ORDER BY category, name"
            )
            rows = cursor.fetchall()
            return [
                Nomenclature(
                    id=row[0],
                    name=row[1],
                    category=row[2],
                    unit=row[3],
                    precision_digits=row[4],
                    created_at=row[5],
                    updated_at=row[6]
                )
                for row in rows
            ]
    return await run_in_threadpool(_get)

@app.post("/api/nomenclature", response_model=Nomenclature)
async def create_nomenclature(item: NomenclatureCreate):
    """Створити номенклатуру"""
    def _create():
        with get_db_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO nomenclature (name, category, unit, precision_digits) OUTPUT INSERTED.id VALUES (?, ?, ?, ?)",
                    (item.name, item.category, item.unit, item.precision_digits)
                )
                new_id = cursor.fetchone()[0]
                conn.commit()
                
                # Fetch created item
                cursor.execute(
                    "SELECT id, name, category, unit, precision_digits, created_at, updated_at FROM nomenclature WHERE id = ?",
                    (new_id,)
                )
                row = cursor.fetchone()
                return Nomenclature(
                    id=row[0],
                    name=row[1],
                    category=row[2],
                    unit=row[3],
                    precision_digits=row[4],
                    created_at=row[5],
                    updated_at=row[6]
                )
            except Exception as e:
                if "UNIQUE" in str(e) or "duplicate" in str(e).lower():
                    raise HTTPException(status_code=400, detail="Номенклатура з такою назвою вже існує")
                raise HTTPException(status_code=500, detail=str(e))
    return await run_in_threadpool(_create)

@app.get("/api/stock/balances", response_model=List[StockBalance])
async def get_balances(category: Optional[str] = None):
    """Отримати залишки"""
    def _get():
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = """
            SELECT 
                n.id, n.name, n.category, n.unit,
                COALESCE(sb.quantity, 0) as quantity,
                COALESCE(sb.last_updated, n.created_at) as last_updated
            FROM nomenclature n
            LEFT JOIN stock_balances sb ON n.id = sb.nomenclature_id
            """
            if category:
                query += " WHERE n.category = ?"
                cursor.execute(query + " ORDER BY n.category, n.name", (category,))
            else:
                cursor.execute(query + " ORDER BY n.category, n.name")
            
            rows = cursor.fetchall()
            return [
                StockBalance(
                    nomenclature_id=row[0],
                    nomenclature_name=row[1],
                    category=row[2],
                    unit=row[3],
                    quantity=float(row[4]),
                    last_updated=row[5]
                )
                for row in rows
            ]
    return await run_in_threadpool(_get)

@app.post("/api/stock/receipt")
async def stock_receipt(operation: StockOperation):
    """Прихід товару на склад"""
    def _receipt():
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check idempotency
            cursor.execute(
                "SELECT id, quantity, price_per_unit FROM stock_movements WHERE idempotency_key = ?",
                (operation.idempotency_key,)
            )
            existing = cursor.fetchone()
            if existing:
                # Validate parameters match
                if abs(existing[1] - operation.quantity) > 0.001:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Конфлікт ідемпотентності: той же ключ з іншими параметрами (кількість: {existing[1]} vs {operation.quantity})"
                    )
                return {"status": "already_processed", "message": "Операція вже оброблена"}
            
            # Get precision
            precision = get_nomenclature_precision(conn, operation.nomenclature_id)
            quantity = round_quantity(operation.quantity, precision)
            
            if quantity <= 0:
                raise HTTPException(status_code=400, detail="Кількість має бути більше нуля")
            
            # Get current balance WITH LOCK
            current_balance = get_current_balance_locked(conn, operation.nomenclature_id)
            new_balance = round_quantity(current_balance + quantity, precision)
            
            # Insert movement
            metadata_json = json.dumps(operation.metadata) if operation.metadata else None
            cursor.execute(
                """INSERT INTO stock_movements 
                   (nomenclature_id, operation_type, quantity, balance_after, price_per_unit, 
                    source_operation_type, source_operation_id, parent_movement_id, idempotency_key, metadata)
                   VALUES (?, 'receipt', ?, ?, ?, ?, ?, ?, ?, ?)""",
                (operation.nomenclature_id, quantity, new_balance, operation.price_per_unit,
                 operation.source_operation_type, operation.source_operation_id, operation.parent_movement_id,
                 operation.idempotency_key, metadata_json)
            )
            
            # Update balance
            update_balance(conn, operation.nomenclature_id, new_balance)
            
            conn.commit()
            return {
                "status": "success",
                "message": "Прихід оброблено успішно",
                "balance_after": new_balance
            }
    return await run_in_threadpool(_receipt)

@app.post("/api/stock/withdrawal")
async def stock_withdrawal(operation: StockOperation):
    """Розхід товару зі складу"""
    def _withdrawal():
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check idempotency
            cursor.execute(
                "SELECT id, quantity FROM stock_movements WHERE idempotency_key = ?",
                (operation.idempotency_key,)
            )
            existing = cursor.fetchone()
            if existing:
                # Validate parameters match
                if abs(existing[1] - operation.quantity) > 0.001:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Конфлікт ідемпотентності: той же ключ з іншими параметрами"
                    )
                return {"status": "already_processed", "message": "Операція вже оброблена"}
            
            # Get precision
            precision = get_nomenclature_precision(conn, operation.nomenclature_id)
            quantity = round_quantity(operation.quantity, precision)
            
            if quantity <= 0:
                raise HTTPException(status_code=400, detail="Кількість має бути більше нуля")
            
            # Get current balance WITH LOCK (prevents race conditions)
            current_balance = get_current_balance_locked(conn, operation.nomenclature_id)
            
            # Check if withdrawal is possible
            if current_balance < quantity:
                cursor.execute(
                    "SELECT name, unit FROM nomenclature WHERE id = ?",
                    (operation.nomenclature_id,)
                )
                nom_row = cursor.fetchone()
                raise HTTPException(
                    status_code=400,
                    detail=f"Недостатньо товару на складі. Доступно: {current_balance} {nom_row[1]}, запитано: {quantity} {nom_row[1]}"
                )
            
            new_balance = round_quantity(current_balance - quantity, precision)
            
            # Insert movement
            metadata_json = json.dumps(operation.metadata) if operation.metadata else None
            cursor.execute(
                """INSERT INTO stock_movements 
                   (nomenclature_id, operation_type, quantity, balance_after, price_per_unit,
                    source_operation_type, source_operation_id, parent_movement_id, idempotency_key, metadata)
                   VALUES (?, 'withdrawal', ?, ?, ?, ?, ?, ?, ?, ?)""",
                (operation.nomenclature_id, quantity, new_balance, operation.price_per_unit,
                 operation.source_operation_type, operation.source_operation_id, operation.parent_movement_id,
                 operation.idempotency_key, metadata_json)
            )
            
            # Update balance
            update_balance(conn, operation.nomenclature_id, new_balance)
            
            conn.commit()
            return {
                "status": "success",
                "message": "Розхід оброблено успішно",
                "balance_after": new_balance
            }
    return await run_in_threadpool(_withdrawal)

@app.get("/api/stock/movements", response_model=List[StockMovement])
async def get_movements(
    nomenclature_id: Optional[int] = None,
    operation_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100
):
    """Отримати журнал рухів"""
    def _get():
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT id, nomenclature_id, operation_type, quantity, balance_after, price_per_unit, idempotency_key, metadata, operation_date, created_at FROM stock_movements WHERE 1=1"
            params = []
            
            if nomenclature_id:
                query += " AND nomenclature_id = ?"
                params.append(nomenclature_id)
            
            if operation_type:
                query += " AND operation_type = ?"
                params.append(operation_type)
            
            if start_date:
                query += " AND operation_date >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND operation_date <= ?"
                params.append(end_date)
            
            query += " ORDER BY operation_date DESC"
            query += f" OFFSET 0 ROWS FETCH NEXT {limit} ROWS ONLY"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [
                StockMovement(
                    id=row[0],
                    nomenclature_id=row[1],
                    operation_type=row[2],
                    quantity=float(row[3]),
                    balance_after=float(row[4]),
                    price_per_unit=float(row[5]) if row[5] else None,
                    idempotency_key=row[6],
                    metadata=row[7],
                    operation_date=row[8],
                    created_at=row[9]
                )
                for row in rows
            ]
    return await run_in_threadpool(_get)

@app.get("/api/stock/movements/export/csv")
async def export_movements_csv(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Експорт журналу в CSV"""
    def _export():
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = """
            SELECT 
                sm.id,
                sm.operation_date,
                sm.operation_type,
                n.name as nomenclature_name,
                n.category,
                sm.quantity,
                n.unit,
                sm.price_per_unit,
                sm.balance_after,
                sm.source_operation_type,
                sm.source_operation_id
            FROM stock_movements sm
            JOIN nomenclature n ON sm.nomenclature_id = n.id
            WHERE 1=1
            """
            params = []
            
            if start_date:
                query += " AND sm.operation_date >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND sm.operation_date <= ?"
                params.append(end_date)
            
            query += " ORDER BY sm.operation_date DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Create CSV
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                'ID', 'Дата', 'Тип операції', 'Номенклатура', 'Категорія',
                'Кількість', 'Од.виміру', 'Ціна', 'Залишок після', 'Джерело', 'ID джерела'
            ])
            
            for row in rows:
                writer.writerow(row)
            
            output.seek(0)
            return output.getvalue()
    
    csv_content = await run_in_threadpool(_export)
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=movements.csv"}
    )

# ... Continue with inventory and sync endpoints (same as before)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
