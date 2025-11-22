"""
Анализ текущей БД перед финальной миграцией
"""
from database import get_db_connection
from dotenv import load_dotenv

load_dotenv()

def analyze_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        print("="*80)
        print("АНАЛИЗ ТЕКУЩЕЙ БАЗЫ ДАННЫХ")
        print("="*80)
        
        # Get all current nomenclature
        cursor.execute("""
            SELECT id, name, category, unit 
            FROM nomenclature 
            ORDER BY category, name
        """)
        
        all_items = cursor.fetchall()
        
        print(f"\nВСЕГО ПОЗИЦИЙ: {len(all_items)}")
        
        # Group by category
        categories = {}
        for item in all_items:
            cat = item[2] if item[2] else "БЕЗ КАТЕГОРИИ"
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)
        
        for cat, items in sorted(categories.items()):
            print(f"\n{cat} - {len(items)} позиций:")
            for item in items:
                print(f"  ID {item[0]}: {item[1]} ({item[3]})")
        
        # Check usage in recipes
        print("\n" + "="*80)
        print("ИСПОЛЬЗОВАНИЕ В РЕЦЕПТАХ")
        print("="*80)
        
        # Check recipe_ingredients
        cursor.execute("""
            SELECT DISTINCT ri.nomenclature_id, n.name
            FROM recipe_ingredients ri
            JOIN nomenclature n ON ri.nomenclature_id = n.id
            ORDER BY n.name
        """)
        
        recipe_ingredients = cursor.fetchall()
        print(f"\nВ recipe_ingredients используется {len(recipe_ingredients)} позиций:")
        for item in recipe_ingredients:
            print(f"  ID {item[0]}: {item[1]}")
        
        # Check recipes target products
        cursor.execute("""
            SELECT DISTINCT r.target_product_id, n.name
            FROM recipes r
            JOIN nomenclature n ON r.target_product_id = n.id
            ORDER BY n.name
        """)
        
        recipe_targets = cursor.fetchall()
        print(f"\nВ recipes (target_product_id) используется {len(recipe_targets)} позиций:")
        for item in recipe_targets:
            print(f"  ID {item[0]}: {item[1]}")
        
        # Check packaging_recipes
        cursor.execute("""
            SELECT DISTINCT pr.source_product_id, n.name
            FROM packaging_recipes pr
            JOIN nomenclature n ON pr.source_product_id = n.id
            WHERE pr.is_active = 1
            ORDER BY n.name
        """)
        
        pkg_sources = cursor.fetchall()
        print(f"\nВ packaging_recipes (source_product_id) используется {len(pkg_sources)} позиций:")
        for item in pkg_sources:
            print(f"  ID {item[0]}: {item[1]}")
        
        cursor.execute("""
            SELECT DISTINCT pr.target_product_id, n.name
            FROM packaging_recipes pr
            JOIN nomenclature n ON pr.target_product_id = n.id
            WHERE pr.is_active = 1
            ORDER BY n.name
        """)
        
        pkg_targets = cursor.fetchall()
        print(f"\nВ packaging_recipes (target_product_id) используется {len(pkg_targets)} позиций:")
        for item in pkg_targets:
            print(f"  ID {item[0]}: {item[1]}")
        
        # Check butchery
        cursor.execute("""
            SELECT DISTINCT br.source_nomenclature_id, n.name
            FROM butchery_recipes br
            JOIN nomenclature n ON br.source_nomenclature_id = n.id
            ORDER BY n.name
        """)
        
        butchery_sources = cursor.fetchall()
        print(f"\nВ butchery_recipes (source) используется {len(butchery_sources)} позиций:")
        for item in butchery_sources:
            print(f"  ID {item[0]}: {item[1]}")
        
        cursor.execute("""
            SELECT DISTINCT bro.output_nomenclature_id, n.name
            FROM butchery_recipe_outputs bro
            JOIN nomenclature n ON bro.output_nomenclature_id = n.id
            ORDER BY n.name
        """)
        
        butchery_outputs = cursor.fetchall()
        print(f"\nВ butchery_recipe_outputs используется {len(butchery_outputs)} позиций:")
        for item in butchery_outputs:
            print(f"  ID {item[0]}: {item[1]}")

if __name__ == "__main__":
    analyze_db()
