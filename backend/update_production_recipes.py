"""
Update production recipes - remove trim step and update nomenclatures
This script updates existing recipes to use butchery output nomenclature
"""
import pyodbc
import json
from database import get_db_connection
from dotenv import load_dotenv

load_dotenv()

def update_recipes():
    """Update all 8 recipes - remove trim, fix nomenclature, renumber steps"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        print("🔄 Updating production recipes...")
        
        # Recipe 1: Бастурма класична - uses Яловичина для бастурми  
        recipe_id = 2  # Known from API
        
        # Delete old steps and ingredients for this recipe
        cursor.execute("DELETE FROM recipe_steps WHERE recipe_id = ?", recipe_id)
        cursor.execute("DELETE FROM recipe_ingredients WHERE recipe_id = ?", recipe_id)
        print(f"✅ Cleared steps for recipe ID {recipe_id}")
        
        steps_basturma = [
            (1, 'salt', 'Засолка', 3, json.dumps({'salt_per_100kg': 20.67, 'water_per_100kg': 66.67, 'massager_minutes': 40})),
            (2, 'wash', 'Промивка', 0.125, json.dumps({'water_usage': '1500L per 80kg', 'duration_hours': 3})),
            (3, 'dry', 'Сушка 1', 1, json.dumps({'type': 'initial'})),
            (4, 'press', 'Прес 1', 1, json.dumps({'press_number': 1})),
            (5, 'dry', 'Сушка 2', 4, json.dumps({'type': 'before_chaman', 'days_min': 3, 'days_max': 4})),
            (6, 'mix', 'Нанесення чаману', 0, json.dumps({'mix_type': 'chaman', 'weight_before_required': True})),
            (7, 'dry', 'Сушка фінальна', 4, json.dumps({'type': 'final', 'days_min': 3, 'days_max': 4}))
        ]
        
        for step_order, step_type, step_name, duration, params in steps_basturma:
            cursor.execute("""
                INSERT INTO recipe_steps (recipe_id, step_order, step_type, step_name, duration_days, parameters)
                VALUES (?, ?, ?, ?, ?, ?)
            """, recipe_id, step_order, step_type, step_name, duration, params)
        
        # Update ingredient to use "Яловичина для бастурми"
        cursor.execute("""
            INSERT INTO recipe_ingredients (recipe_id, nomenclature_id, quantity_per_100kg, is_optional, notes)
            VALUES (?, 199, 100.0, 0, 'Оброблене м''ясо після розділки')
        """, recipe_id)
        
        print(f"✅ Updated recipe: Бастурма класична")
        
        # Recipe 2: Бастурма з конини - uses Конина для бастурми
        recipe_id_horse = 3
        cursor.execute("DELETE FROM recipe_steps WHERE recipe_id = ?", recipe_id_horse)
        cursor.execute("DELETE FROM recipe_ingredients WHERE recipe_id = ?", recipe_id_horse)
        
        steps_horse = [
            (1, 'salt', 'Засолка', 3, json.dumps({'salt_per_100kg': 20.67, 'water_per_100kg': 66.67, 'massager_minutes': 40})),
            (2, 'wash', 'Промивка', 0.125, json.dumps({'water_usage': '1500L per 80kg', 'duration_hours': 3})),
            (3, 'dry', 'Сушка 1', 1, json.dumps({'type': 'initial'})),
            (4, 'sugar', 'Масажер з цукром', 0.083, json.dumps({'sugar_per_kg': 20, 'duration_hours': 2})),
            (5, 'dry', 'В\'ялення', 1, json.dumps({'type': 'curing'})),
            (6, 'press', 'Прес 1', 1, json.dumps({'press_number': 1})),
            (7, 'dry', 'Сушка 2', 4, json.dumps({'type': 'before_marinade', 'days_min': 3, 'days_max': 4})),
            (8, 'mix', 'Нанесення маринаду', 0, json.dumps({'mix_type': 'marinade_horse', 'weight_before_required': True})),
            (9, 'dry', 'Сушка фінальна', 4, json.dumps({'type': 'final', 'days_min': 3, 'days_max': 4}))
        ]
        
        for step_order, step_type, step_name, duration, params in steps_horse:
            cursor.execute("""
                INSERT INTO recipe_steps (recipe_id, step_order, step_type, step_name, duration_days, parameters)
                VALUES (?, ?, ?, ?, ?, ?)
            """, recipe_id_horse, step_order, step_type, step_name, duration, params)
        
        cursor.execute("""
            INSERT INTO recipe_ingredients (recipe_id, nomenclature_id, quantity_per_100kg, is_optional, notes)
            VALUES (?, 202, 100.0, 0, 'Оброблене м''ясо після розділки')
        """, recipe_id_horse)
        
        print(f"✅ Updated recipe: Бастурма з конини")
        
        # Recipe 3: Свинина сировялена - uses Свинина для банкетної
        recipe_id_pork = 6
        cursor.execute("DELETE FROM recipe_steps WHERE recipe_id = ?", recipe_id_pork)
        cursor.execute("DELETE FROM recipe_ingredients WHERE recipe_id = ?", recipe_id_pork)
        
        steps_pork = [
            (1, 'salt', 'Засолка', 3, json.dumps({'salt_per_100kg': 21.0, 'water_per_100kg': 25.0, 'massager_minutes': 40})),
            (2, 'wash', 'Промивка', 0.125, json.dumps({'water_usage': '1000L', 'duration_hours': 3})),
            (3, 'dry', 'Сушка 1', 1, json.dumps({'type': 'initial'})),
            (4, 'press', 'Прес 1', 1, json.dumps({'press_number': 1})),
            (5, 'dry', 'Сушка 2', 4, json.dumps({'days_min': 3, 'days_max': 4})),
            (6, 'mix', 'Нанесення маринаду червоного', 0, json.dumps({'mix_type': 'red_marinade', 'weight_before_required': True})),
            (7, 'dry', 'Сушка фінальна', 4, json.dumps({'days_min': 3, 'days_max': 4}))
        ]
        
        for step_order, step_type, step_name, duration, params in steps_pork:
            cursor.execute("""
                INSERT INTO recipe_steps (recipe_id, step_order, step_type, step_name, duration_days, parameters)
                VALUES (?, ?, ?, ?, ?, ?)
            """, recipe_id_pork, step_order, step_type, step_name, duration, params)
        
        cursor.execute("""
            INSERT INTO recipe_ingredients (recipe_id, nomenclature_id, quantity_per_100kg, is_optional, notes)
            VALUES (?, 207, 100.0, 0, 'Оброблене м''ясо після розділки')
        """, recipe_id_pork)
        
        print(f"✅ Updated recipe: Свинина сировялена")
        
        # Recipe 4: Індичка сировялена - uses Індичка для бастурми
        recipe_id_turkey = 4
        cursor.execute("DELETE FROM recipe_steps WHERE recipe_id = ?", recipe_id_turkey)
        cursor.execute("DELETE FROM recipe_ingredients WHERE recipe_id = ?", recipe_id_turkey)
        
        steps_turkey = [
            (1, 'salt', 'Засолка', 3, json.dumps({'salt_per_100kg': 19.0, 'water_per_100kg': 25.0, 'massager_minutes': 40})),
            (2, 'wash', 'Промивка', 0.125, json.dumps({'water_usage': '800L', 'duration_hours': 3})),
            (3, 'dry', 'Сушка 1', 1, json.dumps({'type': 'initial'})),
            (4, 'press', 'Прес 1', 1, json.dumps({'press_number': 1})),
            (5, 'dry', 'Сушка 2', 4, json.dumps({'days_min': 3, 'days_max': 4})),
            (6, 'mix', 'Нанесення чаману', 0, json.dumps({'mix_type': 'chaman', 'weight_before_required': True})),
            (7, 'dry', 'Сушка фінальна', 4, json.dumps({'days_min': 3, 'days_max': 4}))
        ]
        
        for step_order, step_type, step_name, duration, params in steps_turkey:
            cursor.execute("""
                INSERT INTO recipe_steps (recipe_id, step_order, step_type, step_name, duration_days, parameters)
                VALUES (?, ?, ?, ?, ?, ?)
            """, recipe_id_turkey, step_order, step_type, step_name, duration, params)
        
        cursor.execute("""
            INSERT INTO recipe_ingredients (recipe_id, nomenclature_id, quantity_per_100kg, is_optional, notes)
            VALUES (?, 211, 100.0, 0, 'Оброблене м''ясо після розділки')
        """, recipe_id_turkey)
        
        print(f"✅ Updated recipe: Індичка сировялена")
        
        # Recipe 5: Курка сировялена - uses Курка для суджука (closest match)
        recipe_id_chicken = 5
        cursor.execute("DELETE FROM recipe_steps WHERE recipe_id = ?", recipe_id_chicken)
        cursor.execute("DELETE FROM recipe_ingredients WHERE recipe_id = ?", recipe_id_chicken)
        
        steps_chicken = [
            (1, 'salt', 'Засолка', 3, json.dumps({'salt_per_100kg': 18.0, 'water_per_100kg': 25.0, 'massager_minutes': 40})),
            (2, 'wash', 'Промивка', 0.125, json.dumps({'water_usage': '800L', 'duration_hours': 3})),
            (3, 'dry', 'Сушка 1', 1, json.dumps({'type': 'initial'})),
            (4, 'press', 'Прес 1', 1, json.dumps({'press_number': 1})),
            (5, 'dry', 'Сушка 2', 4, json.dumps({'days_min': 3, 'days_max': 4})),
            (6, 'mix', 'Нанесення чаману', 0, json.dumps({'mix_type': 'chaman', 'weight_before_required': True})),
            (7, 'dry', 'Сушка фінальна', 4, json.dumps({'days_min': 3, 'days_max': 4}))
        ]
        
        for step_order, step_type, step_name, duration, params in steps_chicken:
            cursor.execute("""
                INSERT INTO recipe_steps (recipe_id, step_order, step_type, step_name, duration_days, parameters)
                VALUES (?, ?, ?, ?, ?, ?)
            """, recipe_id_chicken, step_order, step_type, step_name, duration, params)
        
        cursor.execute("""
            INSERT INTO recipe_ingredients (recipe_id, nomenclature_id, quantity_per_100kg, is_optional, notes)
            VALUES (?, 210, 100.0, 0, 'Оброблене м''ясо після розділки')
        """, recipe_id_chicken)
        
        print(f"✅ Updated recipe: Курка сировялена")
        
        # Recipe 6: Пластина яловичина - uses Яловичина для пластин
        recipe_id_plate = cursor.execute("SELECT id FROM recipes WHERE name = 'Пластина яловичина'").fetchone()[0]
        
        steps_plate = [
            (1, 'marinade', 'Виготовлення маринаду', 0, json.dumps({'type': 'beef_plate_marinade'})),
            (2, 'vacuum', 'Вакуумна фасовка та маринування', 6, json.dumps({'package_weight': 3, 'marinate_days_min': 4, 'marinate_days_max': 6})),
            (3, 'press', 'Пресування', 1, json.dumps({'press_number': 1})),
            (4, 'dry', 'Сушка', 3, json.dumps({'days_min': 2, 'days_max': 3}))
        ]
        
        for step_order, step_type, step_name, duration, params in steps_plate:
            cursor.execute("""
                INSERT INTO recipe_steps (recipe_id, step_order, step_type, step_name, duration_days, parameters)
                VALUES (?, ?, ?, ?, ?, ?)
            """, recipe_id_plate, step_order, step_type, step_name, duration, params)
        
        cursor.execute("""
            INSERT INTO recipe_ingredients (recipe_id, nomenclature_id, quantity_per_100kg, is_optional, notes)
            VALUES (?, 200, 100.0, 0, 'Оброблене м''ясо після розділки')
        """, recipe_id_plate)
        
        print(f"✅ Updated recipe: Пластина яловичина")
        
        # Recipe 7: Суджук - uses Яловичина для суджука
        recipe_id_sujuk = cursor.execute("SELECT id FROM recipes WHERE name = 'Суджук ваговий'").fetchone()[0]
        
        steps_sujuk = [
            (1, 'marinade_spices', 'Замішування зі специями', 2, json.dumps({'marinate_days': 2})),
            (2, 'grind', 'Помол м\'яса', 0, json.dumps({'grind_type': 'fine'})),
            (3, 'massage', 'Масажер з водою та барвником', 0, json.dumps({'water_per_100kg': 15, 'dye_per_100kg': 0.25})),
            (4, 'stuff', 'Заправка в кишку', 0, json.dumps({'casing_options': [{'length': 93, 'diameter': '48+', 'capacity': 100}, {'length': 65, 'diameter': '53+', 'capacity': 100}]})),
            (5, 'dry', 'Сушка 1', 3, json.dumps({'days': 3})),
            (6, 'press', 'Прес 1', 1, json.dumps({'press_number': 1})),
            (7, 'dry', 'Сушка 2', 2, json.dumps({'days_min': 1, 'days_max': 2})),
            (8, 'press', 'Прес 2', 1, json.dumps({'press_number': 2})),
            (9, 'dry', 'Сушка фінальна', 4, json.dumps({'days_min': 3, 'days_max': 4}))
        ]
        
        for step_order, step_type, step_name, duration, params in steps_sujuk:
            cursor.execute("""
                INSERT INTO recipe_steps (recipe_id, step_order, step_type, step_name, duration_days, parameters)
                VALUES (?, ?, ?, ?, ?, ?)
            """, recipe_id_sujuk, step_order, step_type, step_name, duration, params)
        
        cursor.execute("""
            INSERT INTO recipe_ingredients (recipe_id, nomenclature_id, quantity_per_100kg, is_optional, notes)
            VALUES (?, 201, 100.0, 0, 'Оброблене м''ясо після розділки')
        """, recipe_id_sujuk)
        
        print(f"✅ Updated recipe: Суджук")
        
        # Recipe 8: Махан - uses Конина для махан
        recipe_id_makhan = cursor.execute("SELECT id FROM recipes WHERE name = 'Махан ваговий'").fetchone()[0]
        
        steps_makhan = [
            (1, 'marinade_first', 'Перший маринад та масажер', 5, json.dumps({'marinate_days': 5, 'cold_storage': True})),
            (2, 'marinade_second', 'Другий маринад з гусарською', 0, json.dumps({'add_gusarska': True})),
            (3, 'stuff', 'Заправка в кишку/оболонку', 0, json.dumps({'no_grinding': True})),
            (4, 'cure', 'В\'ялення в холоді', 10, json.dumps({'days': 10})),
            (5, 'dry', 'Сушка', 10, json.dumps({'days': 10}))
        ]
        
        for step_order, step_type, step_name, duration, params in steps_makhan:
            cursor.execute("""
                INSERT INTO recipe_steps (recipe_id, step_order, step_type, step_name, duration_days, parameters)
                VALUES (?, ?, ?, ?, ?, ?)
            """, recipe_id_makhan, step_order, step_type, step_name, duration, params)
        
        cursor.execute("""
            INSERT INTO recipe_ingredients (recipe_id, nomenclature_id, quantity_per_100kg, is_optional, notes)
            VALUES (?, 204, 100.0, 0, 'Оброблене м''ясо після розділки')
        """, recipe_id_makhan)
        
        print(f"✅ Updated recipe: Махан")
        
        conn.commit()
        print("\n✅ All recipes updated successfully!")
        print("📋 Changes:")
        print("  - Removed 'trim' step from all recipes")
        print("  - Updated nomenclature to use butchery outputs")
        print("  - Renumbered step orders")

if __name__ == "__main__":
    update_recipes()
