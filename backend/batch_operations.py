"""
Batch operations for stock movements
Implements all-or-nothing transactional batch processing
"""
import json
from typing import List, Tuple
from fastapi import HTTPException

def round_quantity(quantity: float, precision: int) -> float:
    """Round quantity based on precision"""
    if precision == 0:
        return float(int(round(quantity)))
    return round(quantity, precision)

def process_batch_receipt(conn, batch_operation, get_nomenclature_precision_func, get_current_balance_locked_func, update_balance_func) -> Tuple[List[dict], List[dict]]:
    """
    Process batch receipt operation
    Returns: (successful_results, failed_results)
    """
    cursor = conn.cursor()
    successful = []
    failed = []
    
    # Check idempotency for entire batch
    cursor.execute(
        "SELECT id FROM stock_movements WHERE idempotency_key = ?",
        (batch_operation.idempotency_key,)
    )
    if cursor.fetchone():
        # Batch already processed
        for item in batch_operation.operations:
            successful.append({
                "nomenclature_id": item.nomenclature_id,
                "status": "already_processed",
                "message": "Операція вже оброблена"
            })
        return successful, failed
    
    # Process each operation
    for idx, item in enumerate(batch_operation.operations):
        try:
            # Get precision
            precision = get_nomenclature_precision_func(conn, item.nomenclature_id)
            quantity = round_quantity(item.quantity, precision)
            
            if quantity <= 0:
                failed.append({
                    "nomenclature_id": item.nomenclature_id,
                    "status": "error",
                    "message": "Кількість має бути більше нуля",
                    "balance_after": None
                })
                if batch_operation.all_or_nothing:
                    raise Exception(f"Validation error for item {idx}: quantity must be positive")
                continue
            
            # Get current balance WITH LOCK
            current_balance = get_current_balance_locked_func(conn, item.nomenclature_id)
            new_balance = round_quantity(current_balance + quantity, precision)
            
            # Create unique idempotency key for this item
            item_key = f"{batch_operation.idempotency_key}-item-{idx}"
            
            # Insert movement
            metadata = item.metadata or {}
            metadata['batch_key'] = batch_operation.idempotency_key
            metadata['batch_index'] = idx
            metadata_json = json.dumps(metadata)
            
            cursor.execute(
                """INSERT INTO stock_movements 
                   (nomenclature_id, operation_type, quantity, balance_after, price_per_unit,
                    source_operation_type, source_operation_id, idempotency_key, metadata)
                   VALUES (?, 'receipt', ?, ?, ?, ?, ?, ?, ?)""",
                (item.nomenclature_id, quantity, new_balance, item.price_per_unit,
                 batch_operation.source_operation_type, batch_operation.source_operation_id,
                 item_key, metadata_json)
            )
            
            # Update balance
            update_balance_func(conn, item.nomenclature_id, new_balance)
            
            successful.append({
                "nomenclature_id": item.nomenclature_id,
                "status": "success",
                "message": "Операція виконана успішно",
                "balance_after": new_balance
            })
            
        except Exception as e:
            error_msg = str(e)
            failed.append({
                "nomenclature_id": item.nomenclature_id,
                "status": "error",
                "message": error_msg,
                "balance_after": None
            })
            
            if batch_operation.all_or_nothing:
                # Rollback entire batch
                raise Exception(f"Batch failed at item {idx}: {error_msg}")
    
    # If we're here and all_or_nothing=True, all operations succeeded
    # Create master record for the batch
    if batch_operation.all_or_nothing and not failed:
        cursor.execute(
            """INSERT INTO stock_movements 
               (nomenclature_id, operation_type, quantity, balance_after, 
                source_operation_type, source_operation_id, idempotency_key, metadata)
               VALUES (?, 'batch_receipt', ?, ?, ?, ?, ?, ?)""",
            (batch_operation.operations[0].nomenclature_id, 0, 0,
             batch_operation.source_operation_type, batch_operation.source_operation_id,
             batch_operation.idempotency_key, json.dumps({"batch_size": len(batch_operation.operations)}))
        )
    
    return successful, failed


def process_batch_withdrawal(conn, batch_operation, get_nomenclature_precision_func, get_current_balance_locked_func, update_balance_func) -> Tuple[List[dict], List[dict]]:
    """
    Process batch withdrawal operation
    Returns: (successful_results, failed_results)
    """
    cursor = conn.cursor()
    successful = []
    failed = []
    
    # Check idempotency for entire batch
    cursor.execute(
        "SELECT id FROM stock_movements WHERE idempotency_key = ?",
        (batch_operation.idempotency_key,)
    )
    if cursor.fetchone():
        # Batch already processed
        for item in batch_operation.operations:
            successful.append({
                "nomenclature_id": item.nomenclature_id,
                "status": "already_processed",
                "message": "Операція вже оброблена"
            })
        return successful, failed
    
    # Process each operation
    for idx, item in enumerate(batch_operation.operations):
        try:
            # Get precision
            precision = get_nomenclature_precision_func(conn, item.nomenclature_id)
            quantity = round_quantity(item.quantity, precision)
            
            if quantity <= 0:
                failed.append({
                    "nomenclature_id": item.nomenclature_id,
                    "status": "error",
                    "message": "Кількість має бути більше нуля",
                    "balance_after": None
                })
                if batch_operation.all_or_nothing:
                    raise Exception(f"Validation error for item {idx}: quantity must be positive")
                continue
            
            # Get current balance WITH LOCK (prevents race conditions!)
            current_balance = get_current_balance_locked_func(conn, item.nomenclature_id)
            
            # Check if withdrawal is possible
            if current_balance < quantity:
                cursor.execute(
                    "SELECT name, unit FROM nomenclature WHERE id = ?",
                    (item.nomenclature_id,)
                )
                nom_row = cursor.fetchone()
                error_msg = f"Недостатньо товару. Доступно: {current_balance} {nom_row[1]}, запитано: {quantity} {nom_row[1]}"
                
                failed.append({
                    "nomenclature_id": item.nomenclature_id,
                    "status": "error",
                    "message": error_msg,
                    "balance_after": None
                })
                
                if batch_operation.all_or_nothing:
                    raise Exception(f"Insufficient stock for item {idx}: {error_msg}")
                continue
            
            new_balance = round_quantity(current_balance - quantity, precision)
            
            # Create unique idempotency key for this item
            item_key = f"{batch_operation.idempotency_key}-item-{idx}"
            
            # Insert movement
            metadata = item.metadata or {}
            metadata['batch_key'] = batch_operation.idempotency_key
            metadata['batch_index'] = idx
            metadata_json = json.dumps(metadata)
            
            cursor.execute(
                """INSERT INTO stock_movements 
                   (nomenclature_id, operation_type, quantity, balance_after, price_per_unit,
                    source_operation_type, source_operation_id, idempotency_key, metadata)
                   VALUES (?, 'withdrawal', ?, ?, ?, ?, ?, ?, ?)""",
                (item.nomenclature_id, quantity, new_balance, item.price_per_unit,
                 batch_operation.source_operation_type, batch_operation.source_operation_id,
                 item_key, metadata_json)
            )
            
            # Update balance
            update_balance_func(conn, item.nomenclature_id, new_balance)
            
            successful.append({
                "nomenclature_id": item.nomenclature_id,
                "status": "success",
                "message": "Операція виконана успішно",
                "balance_after": new_balance
            })
            
        except Exception as e:
            error_msg = str(e)
            failed.append({
                "nomenclature_id": item.nomenclature_id,
                "status": "error",
                "message": error_msg,
                "balance_after": None
            })
            
            if batch_operation.all_or_nothing:
                # Rollback entire batch
                raise Exception(f"Batch failed at item {idx}: {error_msg}")
    
    # If we're here and all_or_nothing=True, all operations succeeded
    # Create master record for the batch
    if batch_operation.all_or_nothing and not failed:
        cursor.execute(
            """INSERT INTO stock_movements 
               (nomenclature_id, operation_type, quantity, balance_after,
                source_operation_type, source_operation_id, idempotency_key, metadata)
               VALUES (?, 'batch_withdrawal', ?, ?, ?, ?, ?, ?)""",
            (batch_operation.operations[0].nomenclature_id, 0, 0,
             batch_operation.source_operation_type, batch_operation.source_operation_id,
             batch_operation.idempotency_key, json.dumps({"batch_size": len(batch_operation.operations)}))
        )
    
    return successful, failed
