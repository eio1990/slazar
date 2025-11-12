from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from typing import List, Optional
from datetime import datetime
import json
import os
from dotenv import load_dotenv

from database import get_db_connection, init_database
from models import (
    NomenclatureCreate, Nomenclature, StockOperation,
    StockMovement, StockBalance, InventorySessionCreate,
    InventorySession, InventoryComplete, SyncBatch,
    BatchStockOperation, BatchResponse, BatchOperationResult
)
from production_api import router as production_router
from packaging_api import router as packaging_router

load_dotenv()

app = FastAPI(title="Склад API")

# Include production router
app.include_router(production_router)

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

def get_current_balance(conn, nomenclature_id: int) -> float:
    """Get current balance for nomenclature"""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT quantity FROM stock_balances WHERE nomenclature_id = ?",
        (nomenclature_id,)
    )
    row = cursor.fetchone()
    return float(row[0]) if row else 0.0

def get_current_balance_locked(conn, nomenclature_id: int) -> float:
    """Get current balance with row lock (prevents race conditions)"""
    cursor = conn.cursor()
    # WITH (UPDLOCK, ROWLOCK) provides row-level exclusive lock in MS SQL
    cursor.execute(
        "SELECT quantity FROM stock_balances WITH (UPDLOCK, ROWLOCK) WHERE nomenclature_id = ?",
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
            "UPDATE stock_balances SET quantity = ?, last_updated = GETUTCDATE() WHERE nomenclature_id = ?",
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
                "SELECT id FROM stock_movements WHERE idempotency_key = ?",
                (operation.idempotency_key,)
            )
            if cursor.fetchone():
                return {"status": "already_processed", "message": "Операція вже оброблена"}
            
            # Get precision
            precision = get_nomenclature_precision(conn, operation.nomenclature_id)
            quantity = round_quantity(operation.quantity, precision)
            
            if quantity <= 0:
                raise HTTPException(status_code=400, detail="Кількість має бути більше нуля")
            
            # Get current balance
            current_balance = get_current_balance(conn, operation.nomenclature_id)
            new_balance = round_quantity(current_balance + quantity, precision)
            
            # Insert movement
            metadata_json = json.dumps(operation.metadata) if operation.metadata else None
            cursor.execute(
                """INSERT INTO stock_movements 
                   (nomenclature_id, operation_type, quantity, balance_after, price_per_unit, idempotency_key, metadata)
                   VALUES (?, 'receipt', ?, ?, ?, ?, ?)""",
                (operation.nomenclature_id, quantity, new_balance, operation.price_per_unit, operation.idempotency_key, metadata_json)
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
                "SELECT id FROM stock_movements WHERE idempotency_key = ?",
                (operation.idempotency_key,)
            )
            if cursor.fetchone():
                return {"status": "already_processed", "message": "Операція вже оброблена"}
            
            # Get precision
            precision = get_nomenclature_precision(conn, operation.nomenclature_id)
            quantity = round_quantity(operation.quantity, precision)
            
            if quantity <= 0:
                raise HTTPException(status_code=400, detail="Кількість має бути більше нуля")
            
            # Get current balance
            current_balance = get_current_balance(conn, operation.nomenclature_id)
            
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
                   (nomenclature_id, operation_type, quantity, balance_after, idempotency_key, metadata)
                   VALUES (?, 'withdrawal', ?, ?, ?, ?)""",
                (operation.nomenclature_id, quantity, new_balance, operation.idempotency_key, metadata_json)
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
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100
):
    """Отримати журнал рухів"""
    def _get():
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT id, nomenclature_id, operation_type, quantity, balance_after, idempotency_key, metadata, operation_date, created_at FROM stock_movements WHERE 1=1"
            params = []
            
            if nomenclature_id:
                query += " AND nomenclature_id = ?"
                params.append(nomenclature_id)
            
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
                    idempotency_key=row[5],
                    metadata=row[6],
                    operation_date=row[7],
                    created_at=row[8]
                )
                for row in rows
            ]
    return await run_in_threadpool(_get)

@app.post("/api/stock/inventory/start", response_model=InventorySession)
async def start_inventory(session: InventorySessionCreate):
    """Почати інвентаризацію"""
    def _start():
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check idempotency
            cursor.execute(
                "SELECT id FROM inventory_sessions WHERE idempotency_key = ?",
                (session.idempotency_key,)
            )
            existing = cursor.fetchone()
            if existing:
                cursor.execute(
                    "SELECT id, session_type, status, started_at, completed_at, idempotency_key, metadata FROM inventory_sessions WHERE id = ?",
                    (existing[0],)
                )
                row = cursor.fetchone()
                return InventorySession(
                    id=row[0],
                    session_type=row[1],
                    status=row[2],
                    started_at=row[3],
                    completed_at=row[4],
                    idempotency_key=row[5],
                    metadata=row[6]
                )
            
            metadata_json = json.dumps(session.metadata) if session.metadata else None
            cursor.execute(
                """INSERT INTO inventory_sessions (session_type, status, idempotency_key, metadata)
                   OUTPUT INSERTED.id VALUES (?, 'in_progress', ?, ?)""",
                (session.session_type, session.idempotency_key, metadata_json)
            )
            new_id = cursor.fetchone()[0]
            conn.commit()
            
            cursor.execute(
                "SELECT id, session_type, status, started_at, completed_at, idempotency_key, metadata FROM inventory_sessions WHERE id = ?",
                (new_id,)
            )
            row = cursor.fetchone()
            return InventorySession(
                id=row[0],
                session_type=row[1],
                status=row[2],
                started_at=row[3],
                completed_at=row[4],
                idempotency_key=row[5],
                metadata=row[6]
            )
    return await run_in_threadpool(_start)

@app.post("/api/stock/inventory/complete")
async def complete_inventory(inventory: InventoryComplete):
    """Завершити інвентаризацію"""
    def _complete():
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if session exists and is in progress
            cursor.execute(
                "SELECT status FROM inventory_sessions WHERE id = ?",
                (inventory.session_id,)
            )
            session_row = cursor.fetchone()
            if not session_row:
                raise HTTPException(status_code=404, detail="Сесія інвентаризації не знайдена")
            
            if session_row[0] == 'completed':
                return {"status": "already_completed", "message": "Інвентаризація вже завершена"}
            
            adjustments = []
            
            for item in inventory.items:
                precision = get_nomenclature_precision(conn, item.nomenclature_id)
                system_quantity = get_current_balance(conn, item.nomenclature_id)
                actual_quantity = round_quantity(item.actual_quantity, precision)
                difference = round_quantity(actual_quantity - system_quantity, precision)
                
                # Save inventory item
                cursor.execute(
                    """INSERT INTO inventory_items 
                       (session_id, nomenclature_id, system_quantity, actual_quantity, difference)
                       VALUES (?, ?, ?, ?, ?)""",
                    (inventory.session_id, item.nomenclature_id, system_quantity, actual_quantity, difference)
                )
                
                # If there's a difference, create adjustment movement
                if difference != 0:
                    operation_type = 'inventory_adjustment_receipt' if difference > 0 else 'inventory_adjustment_withdrawal'
                    movement_key = f"{inventory.idempotency_key}_adj_{item.nomenclature_id}"
                    
                    cursor.execute(
                        """INSERT INTO stock_movements 
                           (nomenclature_id, operation_type, quantity, balance_after, idempotency_key, metadata)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (item.nomenclature_id, abs(difference), actual_quantity, movement_key,
                         json.dumps({"inventory_session_id": inventory.session_id}))
                    )
                    
                    # Update balance
                    update_balance(conn, item.nomenclature_id, actual_quantity)
                    
                    adjustments.append({
                        "nomenclature_id": item.nomenclature_id,
                        "difference": difference,
                        "system_quantity": system_quantity,
                        "actual_quantity": actual_quantity
                    })
            
            # Mark session as completed
            cursor.execute(
                "UPDATE inventory_sessions SET status = 'completed', completed_at = GETUTCDATE() WHERE id = ?",
                (inventory.session_id,)
            )
            
            conn.commit()
            return {
                "status": "success",
                "message": "Інвентаризацію завершено",
                "adjustments_count": len(adjustments),
                "adjustments": adjustments
            }
    return await run_in_threadpool(_complete)

@app.post("/api/stock/receipt/bulk", response_model=BatchResponse)
async def batch_receipt(batch_operation: BatchStockOperation):
    """Масовий прихід товарів"""
    from batch_operations import process_batch_receipt
    
    def _batch():
        try:
            with get_db_connection() as conn:
                successful, failed = process_batch_receipt(
                    conn, batch_operation,
                    get_nomenclature_precision,
                    get_current_balance_locked,
                    update_balance
                )
                
                total = len(batch_operation.operations)
                success_count = len(successful)
                fail_count = len(failed)
                
                results = successful + failed
                
                if fail_count == 0:
                    status = "success"
                    message = f"Всі {total} операцій виконано успішно"
                elif success_count == 0:
                    status = "error"
                    message = f"Всі {total} операцій провалились"
                else:
                    status = "partial_success"
                    message = f"Виконано {success_count} з {total} операцій. Провалено: {fail_count}"
                
                return BatchResponse(
                    status=status,
                    total_operations=total,
                    successful=success_count,
                    failed=fail_count,
                    results=results,
                    message=message
                )
        except Exception as e:
            # Rollback happened (all_or_nothing=True)
            error_msg = str(e)
            return BatchResponse(
                status="error",
                total_operations=len(batch_operation.operations),
                successful=0,
                failed=len(batch_operation.operations),
                results=[
                    {"nomenclature_id": item.nomenclature_id, "status": "error", 
                     "message": f"Batch failed: {error_msg}", "balance_after": None}
                    for item in batch_operation.operations
                ],
                message=f"Batch operation failed: {error_msg}"
            )
    return await run_in_threadpool(_batch)

@app.post("/api/stock/withdrawal/bulk", response_model=BatchResponse)
async def batch_withdrawal(batch_operation: BatchStockOperation):
    """Масовий розхід товарів"""
    from batch_operations import process_batch_withdrawal
    
    def _batch():
        try:
            with get_db_connection() as conn:
                successful, failed = process_batch_withdrawal(
                    conn, batch_operation,
                    get_nomenclature_precision,
                    get_current_balance_locked,
                    update_balance
                )
                
                total = len(batch_operation.operations)
                success_count = len(successful)
                fail_count = len(failed)
                
                results = successful + failed
                
                if fail_count == 0:
                    status = "success"
                    message = f"Всі {total} операцій виконано успішно"
                elif success_count == 0:
                    status = "error"
                    message = f"Всі {total} операцій провалились"
                else:
                    status = "partial_success"
                    message = f"Виконано {success_count} з {total} операцій. Провалено: {fail_count}"
                
                return BatchResponse(
                    status=status,
                    total_operations=total,
                    successful=success_count,
                    failed=fail_count,
                    results=results,
                    message=message
                )
        except Exception as e:
            # Rollback happened (all_or_nothing=True)
            error_msg = str(e)
            return BatchResponse(
                status="error",
                total_operations=len(batch_operation.operations),
                successful=0,
                failed=len(batch_operation.operations),
                results=[
                    {"nomenclature_id": item.nomenclature_id, "status": "error",
                     "message": f"Batch failed: {error_msg}", "balance_after": None}
                    for item in batch_operation.operations
                ],
                message=f"Batch operation failed: {error_msg}"
            )
    return await run_in_threadpool(_batch)

@app.post("/api/sync/operations")
async def sync_operations(batch: SyncBatch):
    """Синхронізувати офлайн операції"""
    results = []
    
    for op in batch.operations:
        try:
            if op.operation_type == "receipt":
                stock_op = StockOperation(**op.data)
                result = await stock_receipt(stock_op)
                results.append({"idempotency_key": op.idempotency_key, "status": "success", "result": result})
            elif op.operation_type == "withdrawal":
                stock_op = StockOperation(**op.data)
                result = await stock_withdrawal(stock_op)
                results.append({"idempotency_key": op.idempotency_key, "status": "success", "result": result})
            else:
                results.append({"idempotency_key": op.idempotency_key, "status": "error", "message": "Невідомий тип операції"})
        except HTTPException as e:
            results.append({"idempotency_key": op.idempotency_key, "status": "error", "message": str(e.detail)})
        except Exception as e:
            results.append({"idempotency_key": op.idempotency_key, "status": "error", "message": str(e)})
    
    return {"results": results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
