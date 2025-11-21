"""
Create packaging recipes for Basturma vagova based on existing pattern
"""
from database import get_db_connection

def create_recipes():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Source: Бастурма вагова (ID 175)
        source_id = 175
        
        # Get existing target products for Basturma
        cursor.execute("""
            SELECT id, name FROM nomenclature 
            WHERE name LIKE 'Бастурма%' AND name NOT LIKE '%вагов%' AND name NOT LIKE '%весов%'
            ORDER BY name
        """)
        
        targets = cursor.fetchall()
        print("Found target products:")
        for t in targets:
            print(f"  {t.id}: {t.name}")
        
        # Get materials from similar recipes
        cursor.execute("""
            SELECT DISTINCT m.id, m.name, m.category
            FROM nomenclature m
            WHERE (m.name LIKE '%Пакет вакуум%' 
                OR m.name LIKE '%Скін%'
                OR m.name LIKE '%Етикетка%'
                OR m.name LIKE '%Термо етикетка%')
            ORDER BY m.name
        """)
        
        materials = cursor.fetchall()
        print("\nAvailable materials:")
        for m in materials:
            print(f"  {m.id}: {m.name}")
        
        # Check what recipes already exist for source 175
        cursor.execute("SELECT target_product_id FROM packaging_recipes WHERE source_product_id = ?", source_id)
        existing = [row[0] for row in cursor.fetchall()]
        print(f"\nExisting recipes for Basturma vagova: {existing}")
        
        print("\n✅ Data collected. Please review and create recipes manually based on existing patterns.")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    create_recipes()
