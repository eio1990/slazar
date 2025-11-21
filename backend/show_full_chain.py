"""
Show full chain: Raw Meat → Semifabricate → Production → Packaging
"""
from database import get_db_connection

def show_chain():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        print("=" * 100)
        print("ПОЛНАЯ ЦЕПОЧКА: СЫРОЕ МЯСО → ПОЛУФАБРИКАТ → ПРОИЗВОДСТВО → ФАСОВКА")
        print("=" * 100)
        
        # Get all production recipes
        cursor.execute("""
            SELECT r.id, r.name, r.target_product_id, n.name as product_name
            FROM recipes r
            JOIN nomenclature n ON r.target_product_id = n.id
            ORDER BY r.name
        """)
        
        recipes = cursor.fetchall()
        
        for recipe in recipes:
            recipe_id = recipe[0]
            recipe_name = recipe[1]
            product_id = recipe[2]
            product_name = recipe[3]
            
            # Get ingredients (semifabricates - напівфабрикати)
            cursor.execute("""
                SELECT n.id, n.name, n.category
                FROM recipe_ingredients ri
                JOIN nomenclature n ON ri.nomenclature_id = n.id
                WHERE ri.recipe_id = ?
                ORDER BY n.name
            """, recipe_id)
            
            all_ingredients = cursor.fetchall()
            semifabricates = [ing for ing in all_ingredients if 'для' in ing[1].lower()]
            
            # For each semifabricate, find source meat via butchery
            meat_sources = set()
            for sf in semifabricates:
                sf_id = sf[0]
                sf_name = sf[1]
                
                cursor.execute("""
                    SELECT br.source_nomenclature_id, n.name as meat_name
                    FROM butchery_recipe_outputs bro
                    JOIN butchery_recipes br ON bro.recipe_id = br.id
                    LEFT JOIN nomenclature n ON br.source_nomenclature_id = n.id
                    WHERE bro.output_nomenclature_id = ?
                """, sf_id)
                
                meat_row = cursor.fetchone()
                if meat_row and meat_row[1]:
                    meat_sources.add(meat_row[1])
            
            # Get packaging results
            cursor.execute("""
                SELECT n.name
                FROM packaging_recipes pr
                JOIN nomenclature n ON pr.target_product_id = n.id
                WHERE pr.source_product_id = ? AND pr.is_active = 1
                ORDER BY n.name
            """, product_id)
            
            packaged = [row[0] for row in cursor.fetchall()]
            
            # Output
            print(f"\n【{recipe_name}】")
            if meat_sources:
                print(f'  "{", ".join(sorted(meat_sources))}"', end='')
            
            if semifabricates:
                sf_names = '", "'.join([sf[1] for sf in semifabricates])
                print(f' - "{sf_names}"', end='')
            
            print(f' - "{product_name}"', end='')
            
            if packaged:
                pkg_list = '", "'.join(packaged)
                print(f' - "{pkg_list}"')
            else:
                print(' - НЕТ ФАСОВКИ')

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    show_chain()
