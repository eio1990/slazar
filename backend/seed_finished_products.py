"""
Seed finished weight products for production module
"""
from database import get_db_connection
from dotenv import load_dotenv

load_dotenv()

def seed_finished_products():
    """Add finished weight products to nomenclature"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        products = [
            ('Бастурма класична вагова', 'Готова продукція - Вагова', 'KG', 3),
            ('Бастурма з конини вагова', 'Готова продукція - Вагова', 'KG', 3),
            ('Індичка сиров\'ялена вагова', 'Готова продукція - Вагова', 'KG', 3),
            ('Курка сиров\'ялена вагова', 'Готова продукція - Вагова', 'KG', 3),
            ('Свинина сиров\'ялена вагова', 'Готова продукція - Вагова', 'KG', 3),
            ('Пластина яловичина вагова', 'Готова продукція - Вагова', 'KG', 3),
            ('Суджук ваговий', 'Готова продукція - Вагова', 'KG', 3),
            ('Махан ваговий', 'Готова продукція - Вагова', 'KG', 3),
            ('Чаман готовий', 'Напівфабрикати', 'KG', 3),
            ('Маринад конь готовий', 'Напівфабрикати', 'KG', 3),
        ]
        
        for name, category, unit, precision in products:
            cursor.execute("""
                IF NOT EXISTS (SELECT 1 FROM nomenclature WHERE name = ?)
                INSERT INTO nomenclature (name, category, unit, precision_digits)
                VALUES (?, ?, ?, ?)
            """, name, name, category, unit, precision)
        
        conn.commit()
        print("✅ Finished products seeded successfully")
        
        # Show what was created
        cursor.execute("""
            SELECT id, name, category 
            FROM nomenclature 
            WHERE category IN ('Готова продукція - Вагова', 'Напівфабрикати')
            ORDER BY id
        """)
        print("\nГотова продукція та напівфабрикати:")
        for row in cursor.fetchall():
            print(f"  {row.id}: {row.name} ({row.category})")

if __name__ == "__main__":
    seed_finished_products()
