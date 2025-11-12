"""
Fix duplicate nomenclature by merging data to original IDs
"""
import pyodbc
from database import get_db_connection

def fix_duplicates():
    """Merge duplicate nomenclature data to original IDs"""
    
    # Mapping: duplicate_id -> original_id
    duplicates = {
        133: 93,   # Бастурма класична вагова -> Бастурма класична
        134: 39,   # Чаман готовий -> Чаман
        135: 41,   # Маринад конь готовий -> Маринад кінь
    }
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        print("="*60)
        print("Fixing duplicate nomenclature...")
        print("="*60)
        
        for duplicate_id, original_id in duplicates.items():
            print(f"\nProcessing duplicate {duplicate_id} -> original {original_id}")
            
            # Get nomenclature info
            cursor.execute("SELECT name, category FROM nomenclature WHERE id = ?", duplicate_id)
            dup_row = cursor.fetchone()
            
            cursor.execute("SELECT name, category FROM nomenclature WHERE id = ?", original_id)
            orig_row = cursor.fetchone()
            
            if not dup_row:
                print(f"  ⚠️  Duplicate {duplicate_id} not found, skipping")
                continue
                
            if not orig_row:
                print(f"  ⚠️  Original {original_id} not found, skipping")
                continue
            
            print(f"  Duplicate: {dup_row.name} ({dup_row.category})")
            print(f"  Original: {orig_row.name} ({orig_row.category})")
            
            # 1. Update stock_movements
            cursor.execute("""
                SELECT COUNT(*) FROM stock_movements 
                WHERE nomenclature_id = ?
            """, duplicate_id)
            movements_count = cursor.fetchone()[0]
            
            if movements_count > 0:
                cursor.execute("""
                    UPDATE stock_movements 
                    SET nomenclature_id = ? 
                    WHERE nomenclature_id = ?
                """, original_id, duplicate_id)
                print(f"  ✅ Updated {movements_count} movements")
            
            # 2. Merge stock_balances
            cursor.execute("""
                SELECT quantity FROM stock_balances 
                WHERE nomenclature_id = ?
            """, duplicate_id)
            dup_balance_row = cursor.fetchone()
            
            cursor.execute("""
                SELECT quantity FROM stock_balances 
                WHERE nomenclature_id = ?
            """, original_id)
            orig_balance_row = cursor.fetchone()
            
            if dup_balance_row:
                dup_qty = float(dup_balance_row[0])
                orig_qty = float(orig_balance_row[0]) if orig_balance_row else 0.0
                new_qty = dup_qty + orig_qty
                
                # Update or insert original balance
                if orig_balance_row:
                    cursor.execute("""
                        UPDATE stock_balances 
                        SET quantity = ?, last_updated = GETUTCDATE()
                        WHERE nomenclature_id = ?
                    """, new_qty, original_id)
                else:
                    cursor.execute("""
                        INSERT INTO stock_balances (nomenclature_id, quantity, last_updated)
                        VALUES (?, ?, GETUTCDATE())
                    """, original_id, new_qty)
                
                # Delete duplicate balance
                cursor.execute("""
                    DELETE FROM stock_balances 
                    WHERE nomenclature_id = ?
                """, duplicate_id)
                
                print(f"  ✅ Merged balances: {dup_qty} + {orig_qty} = {new_qty}")
            
            # 3. Update recipe_ingredients
            cursor.execute("""
                UPDATE recipe_ingredients 
                SET nomenclature_id = ? 
                WHERE nomenclature_id = ?
            """, original_id, duplicate_id)
            
            # 4. Update recipe_spices
            cursor.execute("""
                UPDATE recipe_spices 
                SET nomenclature_id = ? 
                WHERE nomenclature_id = ?
            """, original_id, duplicate_id)
            
            # 5. Update recipes (target_product_id)
            cursor.execute("""
                UPDATE recipes 
                SET target_product_id = ? 
                WHERE target_product_id = ?
            """, original_id, duplicate_id)
            
            # 6. Delete duplicate nomenclature
            cursor.execute("""
                DELETE FROM nomenclature 
                WHERE id = ?
            """, duplicate_id)
            
            print(f"  ✅ Deleted duplicate nomenclature {duplicate_id}")
            
        conn.commit()
        
        print("\n" + "="*60)
        print("✅ All duplicates fixed!")
        print("="*60)
        
        # Verify
        print("\nVerifying final state:")
        for original_id in [93, 39, 41]:
            cursor.execute("""
                SELECT n.name, COALESCE(b.quantity, 0) as qty
                FROM nomenclature n
                LEFT JOIN stock_balances b ON n.id = b.nomenclature_id
                WHERE n.id = ?
            """, original_id)
            row = cursor.fetchone()
            if row:
                print(f"  {original_id}: {row.name} - {row.qty} на складе")

if __name__ == "__main__":
    fix_duplicates()
