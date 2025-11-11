# -*- coding: utf-8 -*-
"""
Seed spices for recipes
"""
from database import get_db_connection
from dotenv import load_dotenv

load_dotenv()

def seed_recipe_spices():
    """Add spices to recipes"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get recipe IDs
        cursor.execute("SELECT id, name FROM recipes")
        recipes = {row.name: row.id for row in cursor.fetchall()}
        
        # Спеціалізовані специї для кожного рецепту
        spices_data = [
            # Бастурма класична - для чаману
            (recipes.get('Бастурма класична'), 19, 1.0, True, 'Пажитник для чаману'),  # Fenugreek
            (recipes.get('Бастурма класична'), 20, 0.5, False, 'Паприка'),
            (recipes.get('Бастурма класична'), 23, 0.3, False, 'Карі'),
            (recipes.get('Бастурма класична'), 25, 0.2, False, 'Часник'),
            
            # Бастурма конини - для маринаду
            (recipes.get('Бастурма з конини вагова'), 19, 1.0, True, 'Пажитник для маринаду'),
            (recipes.get('Бастурма з конини вагова'), 20, 0.5, False, 'Паприка'),
            (recipes.get('Бастурма з конини вагова'), 25, 0.3, False, 'Часник'),
            (recipes.get('Бастурма з конини вагова'), 22, 0.2, False, 'Перець чілі'),
            
            # Індичка
            (recipes.get('Індичка сиров\'ялена'), 10, 2.0, False, 'Соль нітритна'),
            (recipes.get('Індичка сиров\'ялена'), 17, 0.3, False, 'Дозрівач'),
            (recipes.get('Індичка сиров\'ялена'), 11, 0.2, False, 'Біопак-Р'),
            (recipes.get('Індичка сиров\'ялена'), 23, 0.5, False, 'Карі'),
            (recipes.get('Індичка сиров\'ялена'), 25, 0.3, False, 'Часник'),
            (recipes.get('Індичка сиров\'ялена'), 20, 0.4, False, 'Паприка'),
            
            # Курка
            (recipes.get('Курка сиров\'ялена'), 10, 2.0, False, 'Соль нітритна'),
            (recipes.get('Курка сиров\'ялена'), 17, 0.3, False, 'Дозрівач'),
            (recipes.get('Курка сиров\'ялена'), 11, 0.2, False, 'Біопак-Р'),
            (recipes.get('Курка сиров\'ялена'), 23, 0.5, False, 'Карі'),
            (recipes.get('Курка сиров\'ялена'), 25, 0.3, False, 'Часник'),
            (recipes.get('Курка сиров\'ялена'), 16, 0.4, False, 'Прованс'),
            
            # Свинина
            (recipes.get('Свинина сиров\'ялена'), 10, 2.0, False, 'Соль нітритна'),
            (recipes.get('Свинина сиров\'ялена'), 17, 0.3, False, 'Дозрівач'),
            (recipes.get('Свинина сиров\'ялена'), 11, 0.2, False, 'Біопак-Р'),
            (recipes.get('Свинина сиров\'ялена'), 15, 0.5, False, 'Угорська'),
            (recipes.get('Свинина сиров\'ялена'), 25, 0.3, False, 'Часник'),
            
            # Пластина
            (recipes.get('Пластина яловичина'), 10, 2.0, False, 'Соль нітритна'),
            (recipes.get('Пластина яловичина'), 17, 0.3, False, 'Дозрівач'),
            (recipes.get('Пластина яловичина'), 11, 0.2, False, 'Біопак-Р'),
            (recipes.get('Пластина яловичина'), 14, 0.5, False, 'Гусарська'),
            (recipes.get('Пластина яловичина'), 25, 0.3, False, 'Часник'),
            
            # Суджук
            (recipes.get('Суджук ваговий'), 21, 0.5, False, 'Перець чорний'),
            (recipes.get('Суджук ваговий'), 24, 0.3, False, 'Зіра'),
            (recipes.get('Суджук ваговий'), 10, 2.0, False, 'Сіль'),
            (recipes.get('Суджук ваговий'), 25, 0.4, False, 'Часник'),
            
            # Махан
            (recipes.get('Махан ваговий'), 10, 2.0, False, 'Сіль для першого маринаду'),
            (recipes.get('Махан ваговий'), 18, 0.2, False, 'Цукор'),
            (recipes.get('Махан ваговий'), 25, 0.5, False, 'Часник'),
            (recipes.get('Махан ваговий'), 14, 0.6, False, 'Гусарська для другого маринаду'),
        ]
        
        for recipe_id, nomenclature_id, qty, is_fenugreek, notes in spices_data:
            if recipe_id:
                cursor.execute("""
                    IF NOT EXISTS (SELECT 1 FROM recipe_spices WHERE recipe_id = ? AND nomenclature_id = ?)
                    INSERT INTO recipe_spices (recipe_id, nomenclature_id, quantity_per_100kg, is_fenugreek, notes)
                    VALUES (?, ?, ?, ?, ?)
                """, recipe_id, nomenclature_id, recipe_id, nomenclature_id, qty, 1 if is_fenugreek else 0, notes)
        
        conn.commit()
        
        # Show results
        cursor.execute("""
            SELECT r.name, COUNT(rs.id) as spice_count
            FROM recipes r
            LEFT JOIN recipe_spices rs ON r.id = rs.recipe_id
            GROUP BY r.name
            ORDER BY r.name
        """)
        
        print("✅ Специї додано до рецептів:")
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]} специй")

if __name__ == "__main__":
    seed_recipe_spices()
