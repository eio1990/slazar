"""
Create universal 'Стек' nomenclature and update all recipes to use it for by-products.
"""
import pyodbc
from database import get_db_connection
from dotenv import load_dotenv

load_dotenv()

def create_universal_stek():
    """Create universal Stek and update all by-product references"""
    
    waste_id = 217  # Відходи м'ясні - остается для waste
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        print("=" * 60)
        print("CREATE UNIVERSAL STEK")
        print("=" * 60)
        
        # Step 1: Create universal "Стек" nomenclature
        print("\n1. Creating universal 'Стек' nomenclature...")
        cursor.execute("""
            INSERT INTO nomenclature (name, category, unit, precision_digits, created_at, updated_at)
            VALUES (?, ?, ?, ?, DATEADD(HOUR, 2, GETDATE()), DATEADD(HOUR, 2, GETDATE()))
        """, "Стек", "Побічні продукти", "кг", 2)
        
        stek_id = int(cursor.execute("SELECT @@IDENTITY").fetchone()[0])
        print(f"   Created 'Стек' with ID {stek_id}")
        
        # Step 2: Find all by-product outputs currently using waste ID
        print(f"\n2. Finding by-product outputs using waste ID {waste_id}...")
        cursor.execute("""
            SELECT recipe_id, output_nomenclature_id, output_type
            FROM butchery_recipe_outputs
            WHERE output_type = 'by-product' AND output_nomenclature_id = ?
        """, waste_id)
        
        by_products = cursor.fetchall()
        print(f"   Found {len(by_products)} by-product outputs to update")
        for bp in by_products:
            print(f"   - Recipe {bp.recipe_id}: {bp.output_type}")
        
        # Step 3: Update by-product outputs to use Stek
        if by_products:
            print(f"\n3. Updating by-product outputs to use 'Стек' (ID {stek_id})...")
            cursor.execute("""
                UPDATE butchery_recipe_outputs
                SET output_nomenclature_id = ?
                WHERE output_type = 'by-product' AND output_nomenclature_id = ?
            """, stek_id, waste_id)
            
            updated_count = cursor.rowcount
            print(f"   Updated {updated_count} by-product records")
        
        # Step 4: Update any existing operation outputs that are by-products
        print(f"\n4. Checking butchery_operation_outputs for by-products...")
        cursor.execute("""
            SELECT boo.id, boo.operation_id, boo.output_nomenclature_id, bro.output_type
            FROM butchery_operation_outputs boo
            JOIN butchery_operations bo ON boo.operation_id = bo.id
            JOIN butchery_recipe_outputs bro ON bo.recipe_id = bro.recipe_id 
                AND boo.output_nomenclature_id = bro.output_nomenclature_id
            WHERE bro.output_type = 'by-product' AND boo.output_nomenclature_id = ?
        """, waste_id)
        
        operation_outputs = cursor.fetchall()
        print(f"   Found {len(operation_outputs)} operation outputs to update")
        
        if operation_outputs:
            print(f"   Updating to use 'Стек' (ID {stek_id})...")
            cursor.execute("""
                UPDATE boo
                SET boo.output_nomenclature_id = ?
                FROM butchery_operation_outputs boo
                JOIN butchery_operations bo ON boo.operation_id = bo.id
                JOIN butchery_recipe_outputs bro ON bo.recipe_id = bro.recipe_id 
                    AND boo.output_nomenclature_id = bro.output_nomenclature_id
                WHERE bro.output_type = 'by-product' AND boo.output_nomenclature_id = ?
            """, stek_id, waste_id)
            print(f"   Updated {cursor.rowcount} operation output records")
        
        # Commit all changes
        conn.commit()
        
        print("\n" + "=" * 60)
        print("UNIVERSAL STEK CREATED SUCCESSFULLY")
        print("=" * 60)
        print(f"\nBy-product (побічний продукт): Стек (ID {stek_id})")
        print(f"Waste (відходи): Відходи м'ясні (ID {waste_id})")
        print()

if __name__ == "__main__":
    try:
        create_universal_stek()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
