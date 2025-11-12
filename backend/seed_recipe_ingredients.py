"""
Seed script to add recipe ingredients (raw materials) to database
Based on tk_raw sheet from Excel
"""
import pyodbc
from database import get_db_connection

def seed_recipe_ingredients():
    """Add ingredients to recipes based on Excel data"""
    
    # Mapping of DR codes to nomenclature IDs (need to get from DB)
    # We'll query the database to find these
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # First, get nomenclature mapping by code/name
        cursor.execute("SELECT id, name FROM nomenclature")
        nomenclature_map = {}
        for row in cursor.fetchall():
            nomenclature_map[row.name] = row.id
        
        print("Nomenclature mapping loaded:", len(nomenclature_map), "items")
        
        # Recipe ingredients data from tk_raw sheet
        recipe_ingredients = [
            # Recipe 1: Бастурма класична
            (2, "Бастурма класична", "Яловичина вищій ґатунок", 100, False),
            
            # Recipe 2: Бастурма з конини вагова  
            (3, "Бастурма з конини вагова", "Конина вищій ґатунок", 100, False),
            
            # Recipe 3: Індичка сиров'ялена
            (4, "Індичка сиров'ялена", "Індик філе", 100, False),
            
            # Recipe 4: Курка сиров'ялена
            (5, "Курка сиров'ялена", "Курка філе", 100, False),
            
            # Recipe 5: Свинина сиров'ялена
            (6, "Свинина сиров'ялена", "Свинина биток", 100, False),
            
            # Recipe 6: Пластина яловичина
            (7, "Пластина яловичина", "Яловичина вищій ґатунок", 60, False),
            (7, "Пластина яловичина", "Яловичина перший ґатунок", 40, False),
            
            # Recipe 7: Суджук - skip (quantities are 0, variable proportions)
            
            # Recipe 8: Махан
            (9, "Махан ваговий", "Конина вищій ґатунок", 60, False),
            (9, "Махан ваговий", "Конина перший ґатунок", 35, False),
            (9, "Махан ваговий", "Кінський жир", 5, False),
        ]
        
        # Clear existing recipe_ingredients
        print("\nClearing existing recipe_ingredients...")
        cursor.execute("DELETE FROM recipe_ingredients")
        conn.commit()
        
        # Insert new ingredients
        print("\nInserting recipe ingredients...")
        inserted_count = 0
        skipped_count = 0
        
        for recipe_id, recipe_name, ingredient_name, qty_per_100kg, is_optional in recipe_ingredients:
            # Find nomenclature_id
            nomenclature_id = nomenclature_map.get(ingredient_name)
            
            if nomenclature_id is None:
                print(f"  ⚠️  Skipped: {ingredient_name} (not found in nomenclature)")
                skipped_count += 1
                continue
            
            try:
                cursor.execute("""
                    INSERT INTO recipe_ingredients 
                    (recipe_id, nomenclature_id, quantity_per_100kg, is_optional)
                    VALUES (?, ?, ?, ?)
                """, recipe_id, nomenclature_id, qty_per_100kg, is_optional)
                
                print(f"  ✅ Recipe {recipe_id} ({recipe_name}): {ingredient_name} - {qty_per_100kg} kg/100kg")
                inserted_count += 1
                
            except Exception as e:
                print(f"  ❌ Error inserting {ingredient_name}: {e}")
                skipped_count += 1
        
        conn.commit()
        
        print(f"\n{'='*60}")
        print(f"✅ Inserted: {inserted_count} ingredients")
        print(f"⚠️  Skipped: {skipped_count} ingredients")
        print(f"{'='*60}")
        
        # Verify
        print("\nVerifying recipe_ingredients...")
        cursor.execute("""
            SELECT r.name, n.name, ri.quantity_per_100kg
            FROM recipe_ingredients ri
            JOIN recipes r ON ri.recipe_id = r.id
            JOIN nomenclature n ON ri.nomenclature_id = n.id
            ORDER BY r.id, ri.quantity_per_100kg DESC
        """)
        
        current_recipe = None
        for row in cursor.fetchall():
            if row[0] != current_recipe:
                current_recipe = row[0]
                print(f"\n{current_recipe}:")
            print(f"  - {row[1]}: {row[2]} кг/100кг")

if __name__ == "__main__":
    print("Starting recipe ingredients seeding...")
    print("="*60)
    seed_recipe_ingredients()
    print("\n✅ Recipe ingredients seeding completed!")
