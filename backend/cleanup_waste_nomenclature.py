"""
Cleanup script to consolidate waste nomenclature.
Keeps only "Відходи м'ясні" (ID 217) and removes all other waste types.
"""
import pyodbc
from database import get_db_connection
from dotenv import load_dotenv

load_dotenv()

def cleanup_waste_nomenclature():
    """Remove duplicate waste nomenclature and update references"""
    
    # IDs to remove (all waste/stek except "Відходи м'ясні" ID 217)
    waste_ids_to_remove = [198, 195, 194, 197, 216, 215, 214]
    keep_waste_id = 217  # Відходи м'ясні
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        print("=" * 60)
        print("CLEANUP WASTE NOMENCLATURE")
        print("=" * 60)
        
        # Step 1: Check current usage in butchery_recipe_outputs
        print("\n1. Checking current usage in butchery_recipe_outputs...")
        cursor.execute("""
            SELECT recipe_id, output_nomenclature_id, output_type
            FROM butchery_recipe_outputs
            WHERE output_nomenclature_id IN ({})
        """.format(','.join('?' * len(waste_ids_to_remove))), waste_ids_to_remove)
        
        affected_outputs = cursor.fetchall()
        print(f"   Found {len(affected_outputs)} outputs using old waste IDs")
        for output in affected_outputs:
            print(f"   - Recipe {output.recipe_id}: nomenclature {output.output_nomenclature_id} ({output.output_type})")
        
        # Step 2: Update butchery_recipe_outputs to use unified waste ID
        print(f"\n2. Updating butchery_recipe_outputs to use unified waste ID {keep_waste_id}...")
        cursor.execute("""
            UPDATE butchery_recipe_outputs
            SET output_nomenclature_id = ?
            WHERE output_nomenclature_id IN ({})
        """.format(','.join('?' * len(waste_ids_to_remove))), 
        keep_waste_id, *waste_ids_to_remove)
        
        updated_count = cursor.rowcount
        print(f"   Updated {updated_count} output records")
        
        # Step 3: Check for usage in butchery_operation_outputs
        print("\n3. Checking usage in butchery_operation_outputs...")
        cursor.execute("""
            SELECT operation_id, output_nomenclature_id, actual_weight
            FROM butchery_operation_outputs
            WHERE output_nomenclature_id IN ({})
        """.format(','.join('?' * len(waste_ids_to_remove))), waste_ids_to_remove)
        
        operation_outputs = cursor.fetchall()
        print(f"   Found {len(operation_outputs)} operation outputs using old waste IDs")
        
        if operation_outputs:
            print(f"   Updating to use unified waste ID {keep_waste_id}...")
            cursor.execute("""
                UPDATE butchery_operation_outputs
                SET output_nomenclature_id = ?
                WHERE output_nomenclature_id IN ({})
            """.format(','.join('?' * len(waste_ids_to_remove))), 
            keep_waste_id, *waste_ids_to_remove)
            print(f"   Updated {cursor.rowcount} operation output records")
        
        # Step 4: Check for usage in stock_movements
        print("\n4. Checking usage in stock_movements...")
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM stock_movements
            WHERE nomenclature_id IN ({})
        """.format(','.join('?' * len(waste_ids_to_remove))), waste_ids_to_remove)
        
        movement_count = cursor.fetchone().count
        print(f"   Found {movement_count} stock movements using old waste IDs")
        
        if movement_count > 0:
            print(f"   Updating to use unified waste ID {keep_waste_id}...")
            cursor.execute("""
                UPDATE stock_movements
                SET nomenclature_id = ?
                WHERE nomenclature_id IN ({})
            """.format(','.join('?' * len(waste_ids_to_remove))), 
            keep_waste_id, *waste_ids_to_remove)
            print(f"   Updated {cursor.rowcount} stock movement records")
        
        # Step 5: Check for usage in stock_balances
        print("\n5. Checking usage in stock_balances...")
        cursor.execute("""
            SELECT nomenclature_id, quantity
            FROM stock_balances
            WHERE nomenclature_id IN ({})
        """.format(','.join('?' * len(waste_ids_to_remove))), waste_ids_to_remove)
        
        balances = cursor.fetchall()
        print(f"   Found {len(balances)} stock balances for old waste IDs")
        
        if balances:
            # Merge balances into the unified waste ID
            print(f"   Merging balances into unified waste ID {keep_waste_id}...")
            for balance in balances:
                print(f"   - Merging {balance.quantity} kg from ID {balance.nomenclature_id}")
                
                # Check if balance exists for keep_waste_id
                cursor.execute("""
                    SELECT quantity FROM stock_balances WHERE nomenclature_id = ?
                """, keep_waste_id)
                
                existing = cursor.fetchone()
                if existing:
                    # Update existing balance
                    new_quantity = existing.quantity + balance.quantity
                    cursor.execute("""
                        UPDATE stock_balances
                        SET quantity = ?, last_updated = DATEADD(HOUR, 2, GETDATE())
                        WHERE nomenclature_id = ?
                    """, new_quantity, keep_waste_id)
                    print(f"     Updated existing balance: {existing.quantity} + {balance.quantity} = {new_quantity}")
                else:
                    # Create new balance
                    cursor.execute("""
                        INSERT INTO stock_balances (nomenclature_id, quantity, last_updated)
                        VALUES (?, ?, DATEADD(HOUR, 2, GETDATE()))
                    """, keep_waste_id, balance.quantity)
                    print(f"     Created new balance: {balance.quantity}")
            
            # Delete old balances
            cursor.execute("""
                DELETE FROM stock_balances
                WHERE nomenclature_id IN ({})
            """.format(','.join('?' * len(waste_ids_to_remove))), waste_ids_to_remove)
            print(f"   Deleted {cursor.rowcount} old balance records")
        
        # Step 6: Delete old nomenclature entries
        print("\n6. Deleting old waste nomenclature entries...")
        cursor.execute("""
            SELECT id, name FROM nomenclature
            WHERE id IN ({})
        """.format(','.join('?' * len(waste_ids_to_remove))), waste_ids_to_remove)
        
        to_delete = cursor.fetchall()
        for item in to_delete:
            print(f"   - Deleting: {item.name} (ID {item.id})")
        
        cursor.execute("""
            DELETE FROM nomenclature
            WHERE id IN ({})
        """.format(','.join('?' * len(waste_ids_to_remove))), waste_ids_to_remove)
        
        print(f"   Deleted {cursor.rowcount} nomenclature records")
        
        # Commit all changes
        conn.commit()
        
        print("\n" + "=" * 60)
        print("CLEANUP COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print(f"\nKept only: Відходи м'ясні (ID {keep_waste_id})")
        print(f"Removed IDs: {waste_ids_to_remove}")
        print()

if __name__ == "__main__":
    try:
        cleanup_waste_nomenclature()
    except Exception as e:
        print(f"\n❌ Error during cleanup: {e}")
        import traceback
        traceback.print_exc()
