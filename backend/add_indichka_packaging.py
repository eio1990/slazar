"""
Add packaging recipes for Індичка
"""
from database import get_db_connection

def add_indichka_recipes():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Source: Індичка сиров'ялена (ID 106)
        source_id = 106
        
        # Target products (already exist)
        targets = [
            (115, 50, 'vacuum'),  # Індичка сиров'ялена 50г вакуум
            (127, 50, 'skin'),    # Індичка сиров'ялена скін 50г
            (128, 60, 'skin'),    # Індичка сиров'ялена скін 60 г
        ]
        
        # Materials
        vacuum_bag_id = 142  # Пакет вакуум 100*200
        skin_tray_id = 148   # Скін лоток нижній
        skin_film_id = 149   # Скін плівка верхня
        thermo_label_id = 144  # Термо етикетка
        
        # Check/create label for indichka
        cursor.execute("SELECT id FROM nomenclature WHERE name LIKE '%тикетка%ндич%'")
        indichka_label = cursor.fetchone()
        
        if not indichka_label:
            cursor.execute("""
                INSERT INTO nomenclature (name, category, unit)
                VALUES ('Етикетка Індичка 75*75', 'Матеріали', 'шт')
            """)
            indichka_label_id = int(cursor.execute("SELECT @@IDENTITY").fetchone()[0])
            print(f"✅ Created label: Етикетка Індичка (ID {indichka_label_id})")
        else:
            indichka_label_id = indichka_label[0]
            print(f"✅ Found label: ID {indichka_label_id}")
        
        # Create packaging recipes
        for target_id, weight, pkg_type in targets:
            cursor.execute("SELECT name FROM nomenclature WHERE id = ?", target_id)
            target_name = cursor.fetchone()[0]
            
            # Check if exists
            cursor.execute("""
                SELECT id FROM packaging_recipes 
                WHERE source_product_id = ? AND target_product_id = ?
            """, source_id, target_id)
            
            if cursor.fetchone():
                print(f"Recipe exists: {target_name}")
                continue
            
            # Create recipe
            cursor.execute("""
                INSERT INTO packaging_recipes (
                    source_product_id, target_product_id,
                    packaging_type, target_weight_grams, is_active
                ) VALUES (?, ?, ?, ?, 1)
            """, source_id, target_id, pkg_type, weight)
            
            recipe_id = int(cursor.execute("SELECT @@IDENTITY").fetchone()[0])
            print(f"✅ Created recipe {recipe_id}: Індичка → {target_name}")
            
            # Add materials
            if pkg_type == 'vacuum':
                # Vacuum packaging
                cursor.execute("""
                    INSERT INTO packaging_recipe_materials (recipe_id, material_id, quantity_per_unit, material_type)
                    VALUES (?, ?, 1, 'packaging')
                """, recipe_id, vacuum_bag_id)
                cursor.execute("""
                    INSERT INTO packaging_recipe_materials (recipe_id, material_id, quantity_per_unit, material_type)
                    VALUES (?, ?, 1, 'label')
                """, recipe_id, indichka_label_id)
                print(f"  Added materials: vacuum bag + label")
            else:
                # Skin packaging
                cursor.execute("""
                    INSERT INTO packaging_recipe_materials (recipe_id, material_id, quantity_per_unit, material_type)
                    VALUES (?, ?, 1, 'packaging')
                """, recipe_id, skin_tray_id)
                cursor.execute("""
                    INSERT INTO packaging_recipe_materials (recipe_id, material_id, quantity_per_unit, material_type)
                    VALUES (?, ?, 1, 'packaging')
                """, recipe_id, skin_film_id)
                cursor.execute("""
                    INSERT INTO packaging_recipe_materials (recipe_id, material_id, quantity_per_unit, material_type)
                    VALUES (?, ?, 1, 'label')
                """, recipe_id, indichka_label_id)
                cursor.execute("""
                    INSERT INTO packaging_recipe_materials (recipe_id, material_id, quantity_per_unit, material_type)
                    VALUES (?, ?, 1, 'label')
                """, recipe_id, thermo_label_id)
                print(f"  Added materials: skin tray + film + labels")
        
        # Add 'Індичка вагова' as result
        cursor.execute("SELECT id FROM nomenclature WHERE name = ?", "Індичка вагова")
        indichka_vagova = cursor.fetchone()
        
        if not indichka_vagova:
            cursor.execute("""
                INSERT INTO nomenclature (name, category, unit)
                VALUES ('Індичка вагова', 'Готова продукція', 'кг')
            """)
            indichka_vagova_id = int(cursor.execute("SELECT @@IDENTITY").fetchone()[0])
            print(f"✅ Created: Індичка вагова (ID {indichka_vagova_id})")
        else:
            indichka_vagova_id = indichka_vagova[0]
        
        # Create recipe for vagova
        cursor.execute("""
            SELECT id FROM packaging_recipes 
            WHERE source_product_id = ? AND target_product_id = ?
        """, source_id, indichka_vagova_id)
        
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO packaging_recipes (
                    source_product_id, target_product_id,
                    packaging_type, target_weight_grams, is_active
                ) VALUES (?, ?, 'vacuum_bulk', 0, 1)
            """, source_id, indichka_vagova_id)
            recipe_id = int(cursor.execute("SELECT @@IDENTITY").fetchone()[0])
            
            # Add materials for vagova (large bag + label + lunch box)
            cursor.execute("""
                INSERT INTO packaging_recipe_materials (recipe_id, material_id, quantity_per_unit, material_type)
                VALUES (?, 150, 1, 'packaging')
            """, recipe_id)
            cursor.execute("""
                INSERT INTO packaging_recipe_materials (recipe_id, material_id, quantity_per_unit, material_type)
                VALUES (?, ?, 1, 'label')
            """, recipe_id, indichka_label_id)
            cursor.execute("""
                INSERT INTO packaging_recipe_materials (recipe_id, material_id, quantity_per_unit, material_type)
                VALUES (?, 141, 1, 'packaging')
            """, recipe_id)
            
            print(f"✅ Created recipe: Індичка → Індичка вагова")
        
        conn.commit()
        print("\n✅ Індичка packaging recipes created!")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    add_indichka_recipes()
