"""
Seed packaging recipes for Basturma
Creates packaged SKUs and their packaging recipes with materials
"""
import pyodbc
from database import get_db_connection

def seed_packaging_recipes():
    """Create packaging recipes for Basturma bulk product"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Source product: Бастурма вагова (ID 175)
        source_product_id = 175
        
        # Check if it exists
        cursor.execute("SELECT id, name FROM nomenclature WHERE id = ?", source_product_id)
        source = cursor.fetchone()
        if not source:
            print(f"ERROR: Source product {source_product_id} not found!")
            return
        
        print(f"Source product: {source.name} (ID: {source.id})")
        
        # Create packaged SKUs (target products) if they don't exist
        packaged_products = [
            ("Бастурма 50г вакуум", 50, "вакуум"),
            ("Бастурма 100г вакуум", 100, "вакуум"),
            ("Бастурма 150г вакуум", 150, "вакуум"),
            ("Бастурма 200г скін", 200, "скін"),
            ("Бастурма 300г скін", 300, "скін"),
        ]
        
        target_ids = {}
        
        for name, weight, pkg_type in packaged_products:
            # Check if exists
            cursor.execute("SELECT id FROM nomenclature WHERE name = ?", name)
            existing = cursor.fetchone()
            
            if existing:
                target_ids[(weight, pkg_type)] = existing.id
                print(f"  Found existing: {name} (ID: {existing.id})")
            else:
                # Create new nomenclature
                cursor.execute("""
                    INSERT INTO nomenclature (name, category, unit)
                    VALUES (?, 'Готова продукція', 'шт')
                """, name)
                new_id = int(cursor.execute("SELECT @@IDENTITY").fetchone()[0])
                target_ids[(weight, pkg_type)] = new_id
                print(f"  Created: {name} (ID: {new_id})")
        
        conn.commit()
        
        # Get or create packaging materials
        materials = {}
        
        # Vacuum bags
        cursor.execute("SELECT id FROM nomenclature WHERE name LIKE '%Пакет вакуум%'")
        vacuum_bag = cursor.fetchone()
        if not vacuum_bag:
            cursor.execute("""
                INSERT INTO nomenclature (name, category, unit, is_raw_material)
                VALUES ('Пакет вакуумний', 'Матеріали', 'шт', 0)
            """)
            materials['vacuum_bag'] = int(cursor.execute("SELECT @@IDENTITY").fetchone()[0])
            print(f"  Created material: Пакет вакуумний (ID: {materials['vacuum_bag']})")
        else:
            materials['vacuum_bag'] = vacuum_bag.id
            print(f"  Found material: Пакет вакуумний (ID: {vacuum_bag.id})")
        
        # Skin packaging
        cursor.execute("SELECT id FROM nomenclature WHERE name LIKE '%Плівка скін%'")
        skin_film = cursor.fetchone()
        if not skin_film:
            cursor.execute("""
                INSERT INTO nomenclature (name, category, unit, is_raw_material)
                VALUES ('Плівка скін', 'Матеріали', 'м', 0)
            """)
            materials['skin_film'] = int(cursor.execute("SELECT @@IDENTITY").fetchone()[0])
            print(f"  Created material: Плівка скін (ID: {materials['skin_film']})")
        else:
            materials['skin_film'] = skin_film.id
            print(f"  Found material: Плівка скін (ID: {skin_film.id})")
        
        # Labels
        cursor.execute("SELECT id FROM nomenclature WHERE name LIKE '%Етикетка%'")
        label = cursor.fetchone()
        if not label:
            cursor.execute("""
                INSERT INTO nomenclature (name, category, unit, is_raw_material)
                VALUES ('Етикетка', 'Матеріали', 'шт', 0)
            """)
            materials['label'] = int(cursor.execute("SELECT @@IDENTITY").fetchone()[0])
            print(f"  Created material: Етикетка (ID: {materials['label']})")
        else:
            materials['label'] = label.id
            print(f"  Found material: Етикетка (ID: {label.id})")
        
        conn.commit()
        
        # Create packaging recipes
        recipes_data = [
            # (weight_grams, pkg_type, materials_per_unit)
            (50, "вакуум", [(materials['vacuum_bag'], 1, 'packaging'), (materials['label'], 1, 'label')]),
            (100, "вакуум", [(materials['vacuum_bag'], 1, 'packaging'), (materials['label'], 1, 'label')]),
            (150, "вакуум", [(materials['vacuum_bag'], 1, 'packaging'), (materials['label'], 1, 'label')]),
            (200, "скін", [(materials['skin_film'], 0.15, 'packaging'), (materials['label'], 1, 'label')]),
            (300, "скін", [(materials['skin_film'], 0.20, 'packaging'), (materials['label'], 1, 'label')]),
        ]
        
        for weight, pkg_type, mats in recipes_data:
            target_id = target_ids[(weight, pkg_type)]
            
            # Check if recipe exists
            cursor.execute("""
                SELECT id FROM packaging_recipes 
                WHERE source_product_id = ? AND target_product_id = ?
            """, source_product_id, target_id)
            
            existing_recipe = cursor.fetchone()
            
            if existing_recipe:
                recipe_id = existing_recipe.id
                print(f"  Recipe exists for {weight}г {pkg_type} (ID: {recipe_id})")
            else:
                # Create recipe
                cursor.execute("""
                    INSERT INTO packaging_recipes (
                        source_product_id, target_product_id, 
                        packaging_type, target_weight_grams, is_active
                    )
                    VALUES (?, ?, ?, ?, 1)
                """, source_product_id, target_id, pkg_type, weight)
                
                recipe_id = int(cursor.execute("SELECT @@IDENTITY").fetchone()[0])
                print(f"  Created recipe for {weight}г {pkg_type} (ID: {recipe_id})")
                
                # Add materials to recipe
                for mat_id, qty, mat_type in mats:
                    cursor.execute("""
                        INSERT INTO packaging_recipe_materials (
                            recipe_id, material_id, quantity_per_unit, 
                            rounding_precision, material_type
                        )
                        VALUES (?, ?, ?, ?, ?)
                    """, recipe_id, mat_id, qty, 1 if mat_type == 'label' else None, mat_type)
                    print(f"    Added material: {mat_id}, qty: {qty}")
        
        conn.commit()
        print("\\n✅ Packaging recipes seeded successfully!")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    seed_packaging_recipes()
