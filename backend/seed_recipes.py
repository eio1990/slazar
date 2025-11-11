"""
Seed recipes data for production module
This script populates the recipes, recipe_ingredients, recipe_spices, and recipe_steps tables
"""
import pyodbc
import json
from database import get_db_connection
from dotenv import load_dotenv

load_dotenv()

def seed_recipes():
    """Seed recipes for all 8 products"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Recipe 1: Бастурма класична (Basturma classic)
        cursor.execute("""
            IF NOT EXISTS (SELECT 1 FROM recipes WHERE name = 'Бастурма класична')
            BEGIN
                INSERT INTO recipes (name, target_product_id, expected_yield_min, expected_yield_max, description)
                VALUES ('Бастурма класична', 
                       (SELECT id FROM nomenclature WHERE name = 'Бастурма класична вагова'),
                       73.0, 78.0, 
                       'Класична яловича бастурма з чаманом')
            END
        """)
        
        recipe_id = cursor.execute("SELECT id FROM recipes WHERE name = 'Бастурма класична'").fetchone()[0]
        
        # Steps for Basturma classic
        steps_basturma = [
            (1, 'trim', 'Обрізка та підготовка', 0, json.dumps({'trim_percent_min': 0, 'trim_percent_max': 0})),
            (2, 'salt', 'Засолка', 3, json.dumps({'salt_per_100kg': 20.67, 'water_per_100kg': 66.67, 'massager_minutes': 40})),
            (3, 'wash', 'Промивка', 0.125, json.dumps({'water_usage': '1500L per 80kg', 'duration_hours': 3})),
            (4, 'dry', 'Сушка 1', 1, json.dumps({'type': 'initial'})),
            (5, 'press', 'Прес 1', 1, json.dumps({'press_number': 1})),
            (6, 'dry', 'Сушка 2', 4, json.dumps({'type': 'before_chaman', 'days_min': 3, 'days_max': 4})),
            (7, 'mix', 'Нанесення чаману', 0, json.dumps({'mix_type': 'chaman', 'weight_before_required': True})),
            (8, 'dry', 'Сушка фінальна', 4, json.dumps({'type': 'final', 'days_min': 3, 'days_max': 4}))
        ]
        
        for step_order, step_type, step_name, duration, params in steps_basturma:
            cursor.execute("""
                IF NOT EXISTS (SELECT 1 FROM recipe_steps WHERE recipe_id = ? AND step_order = ?)
                INSERT INTO recipe_steps (recipe_id, step_order, step_type, step_name, duration_days, parameters)
                VALUES (?, ?, ?, ?, ?, ?)
            """, recipe_id, step_order, recipe_id, step_order, step_type, step_name, duration, params)
        
        # Ingredients for Basturma (primary meat)
        cursor.execute("""
            IF NOT EXISTS (SELECT 1 FROM recipe_ingredients WHERE recipe_id = ? AND nomenclature_id = (SELECT id FROM nomenclature WHERE name = 'Яловичина вищій ґатунок'))
            INSERT INTO recipe_ingredients (recipe_id, nomenclature_id, quantity_per_100kg, is_optional, notes)
            VALUES (?, (SELECT id FROM nomenclature WHERE name = 'Яловичина вищій ґатунок'), 100.0, 0, 'Основна сировина')
        """, recipe_id, recipe_id)
        
        # Spices for salting
        cursor.execute("""
            IF NOT EXISTS (SELECT 1 FROM recipe_spices WHERE recipe_id = ? AND nomenclature_id = (SELECT id FROM nomenclature WHERE name = 'Сіль'))
            INSERT INTO recipe_spices (recipe_id, nomenclature_id, quantity_per_100kg, is_fenugreek, notes)
            VALUES (?, (SELECT id FROM nomenclature WHERE name = 'Сіль'), 20.67, 0, 'Для засолки')
        """, recipe_id, recipe_id)
        
        # Water for salting
        cursor.execute("""
            IF NOT EXISTS (SELECT 1 FROM recipe_spices WHERE recipe_id = ? AND nomenclature_id = (SELECT id FROM nomenclature WHERE name = 'Вода'))
            INSERT INTO recipe_spices (recipe_id, nomenclature_id, quantity_per_100kg, is_fenugreek, notes)
            VALUES (?, (SELECT id FROM nomenclature WHERE name = 'Вода'), 66.67, 0, 'Для засолки')
        """, recipe_id, recipe_id)
        
        # Recipe 2: Бастурма з конини (Basturma horse)
        cursor.execute("""
            IF NOT EXISTS (SELECT 1 FROM recipes WHERE name = 'Бастурма з конини вагова')
            BEGIN
                INSERT INTO recipes (name, target_product_id, expected_yield_min, expected_yield_max, description)
                VALUES ('Бастурма з конини вагова', 
                       (SELECT id FROM nomenclature WHERE name = 'Конина вищий ґатунок'),
                       67.0, 68.0, 
                       'Бастурма з конини з маринадом')
            END
        """)
        
        recipe_id_horse = cursor.execute("SELECT id FROM recipes WHERE name = 'Бастурма з конини вагова'").fetchone()[0]
        
        # Steps for horse basturma
        steps_horse = [
            (1, 'trim', 'Обрізка та підготовка', 0, json.dumps({'trim_percent_min': 0, 'trim_percent_max': 0})),
            (2, 'salt', 'Засолка', 3, json.dumps({'salt_per_100kg': 20.67, 'water_per_100kg': 66.67, 'massager_minutes': 40})),
            (3, 'wash', 'Промивка', 0.125, json.dumps({'water_usage': '1500L per 80kg', 'duration_hours': 3})),
            (4, 'dry', 'Сушка 1', 1, json.dumps({'type': 'initial'})),
            (5, 'sugar', 'Масажер з цукром', 0.083, json.dumps({'sugar_per_kg': 20, 'duration_hours': 2})),
            (6, 'dry', 'В\'ялення', 1, json.dumps({'type': 'curing'})),
            (7, 'press', 'Прес 1', 1, json.dumps({'press_number': 1})),
            (8, 'dry', 'Сушка 2', 4, json.dumps({'type': 'before_marinade', 'days_min': 3, 'days_max': 4})),
            (9, 'mix', 'Нанесення маринаду', 0, json.dumps({'mix_type': 'marinade_horse', 'weight_before_required': True})),
            (10, 'dry', 'Сушка фінальна', 4, json.dumps({'type': 'final', 'days_min': 3, 'days_max': 4}))
        ]
        
        for step_order, step_type, step_name, duration, params in steps_horse:
            cursor.execute("""
                IF NOT EXISTS (SELECT 1 FROM recipe_steps WHERE recipe_id = ? AND step_order = ?)
                INSERT INTO recipe_steps (recipe_id, step_order, step_type, step_name, duration_days, parameters)
                VALUES (?, ?, ?, ?, ?, ?)
            """, recipe_id_horse, step_order, recipe_id_horse, step_order, step_type, step_name, duration, params)
        
        # Recipe 3: Індичка (Turkey)
        cursor.execute("""
            IF NOT EXISTS (SELECT 1 FROM recipes WHERE name = 'Індичка сиров\'ялена вагова')
            BEGIN
                INSERT INTO recipes (name, target_product_id, expected_yield_min, expected_yield_max, description)
                VALUES ('Індичка сиров\'ялена вагова', 
                       (SELECT id FROM nomenclature WHERE name = 'Індик філе'),
                       58.0, 61.0, 
                       'Сиров\'ялена індичка')
            END
        """)
        
        recipe_id_turkey = cursor.execute("SELECT id FROM recipes WHERE name = 'Індичка сиров\'ялена вагова'").fetchone()[0]
        
        steps_turkey = [
            (1, 'trim', 'Обрізка філе', 0, json.dumps({'trim_percent_min': 7, 'trim_percent_max': 10})),
            (2, 'marinade', 'Виготовлення маринаду', 0, json.dumps({'type': 'turkey_marinade'})),
            (3, 'vacuum', 'Вакуумна фасовка та маринування', 6, json.dumps({'package_weight': 3, 'marinate_days_min': 5, 'marinate_days_max': 6})),
            (4, 'press', 'Пресування', 1, json.dumps({'press_number': 1})),
            (5, 'dry', 'Сушка', 5, json.dumps({'days_min': 3, 'days_max': 5}))
        ]
        
        for step_order, step_type, step_name, duration, params in steps_turkey:
            cursor.execute("""
                IF NOT EXISTS (SELECT 1 FROM recipe_steps WHERE recipe_id = ? AND step_order = ?)
                INSERT INTO recipe_steps (recipe_id, step_order, step_type, step_name, duration_days, parameters)
                VALUES (?, ?, ?, ?, ?, ?)
            """, recipe_id_turkey, step_order, recipe_id_turkey, step_order, step_type, step_name, duration, params)
        
        # Recipe 4: Курка (Chicken)
        cursor.execute("""
            IF NOT EXISTS (SELECT 1 FROM recipes WHERE name = 'Курка сиров\'ялена вагова')
            BEGIN
                INSERT INTO recipes (name, target_product_id, expected_yield_min, expected_yield_max, description)
                VALUES ('Курка сиров\'ялена вагова', 
                       (SELECT id FROM nomenclature WHERE name = 'Курка філе'),
                       53.0, 55.0, 
                       'Сиров\'ялена курка')
            END
        """)
        
        recipe_id_chicken = cursor.execute("SELECT id FROM recipes WHERE name = 'Курка сиров\'ялена вагова'").fetchone()[0]
        
        steps_chicken = [
            (1, 'trim', 'Обрізка філе', 0, json.dumps({'trim_percent_min': 22, 'trim_percent_max': 25})),
            (2, 'marinade', 'Виготовлення маринаду', 0, json.dumps({'type': 'chicken_marinade'})),
            (3, 'vacuum', 'Вакуумна фасовка та маринування', 5, json.dumps({'package_weight': 3, 'marinate_days_min': 4, 'marinate_days_max': 5})),
            (4, 'press', 'Пресування', 1, json.dumps({'press_number': 1})),
            (5, 'dry', 'Сушка', 3, json.dumps({'days_min': 2, 'days_max': 3}))
        ]
        
        for step_order, step_type, step_name, duration, params in steps_chicken:
            cursor.execute("""
                IF NOT EXISTS (SELECT 1 FROM recipe_steps WHERE recipe_id = ? AND step_order = ?)
                INSERT INTO recipe_steps (recipe_id, step_order, step_type, step_name, duration_days, parameters)
                VALUES (?, ?, ?, ?, ?, ?)
            """, recipe_id_chicken, step_order, recipe_id_chicken, step_order, step_type, step_name, duration, params)
        
        # Recipe 5: Свинина (Pork)
        cursor.execute("""
            IF NOT EXISTS (SELECT 1 FROM recipes WHERE name = 'Свинина сиров\'ялена вагова')
            BEGIN
                INSERT INTO recipes (name, target_product_id, expected_yield_min, expected_yield_max, description)
                VALUES ('Свинина сиров\'ялена вагова', 
                       (SELECT id FROM nomenclature WHERE name = 'Свинина биток'),
                       62.0, 64.0, 
                       'Сиров\'ялена свинина')
            END
        """)
        
        recipe_id_pork = cursor.execute("SELECT id FROM recipes WHERE name = 'Свинина сиров\'ялена вагова'").fetchone()[0]
        
        steps_pork = [
            (1, 'trim', 'Обрізка', 0, json.dumps({'trim_percent_min': 15, 'trim_percent_max': 20})),
            (2, 'marinade', 'Виготовлення маринаду', 0, json.dumps({'type': 'pork_marinade'})),
            (3, 'vacuum', 'Вакуумна фасовка та маринування', 6, json.dumps({'package_weight': 3, 'marinate_days_min': 5, 'marinate_days_max': 6})),
            (4, 'press', 'Пресування', 1, json.dumps({'press_number': 1})),
            (5, 'dry', 'Сушка', 6, json.dumps({'days_min': 5, 'days_max': 6}))
        ]
        
        for step_order, step_type, step_name, duration, params in steps_pork:
            cursor.execute("""
                IF NOT EXISTS (SELECT 1 FROM recipe_steps WHERE recipe_id = ? AND step_order = ?)
                INSERT INTO recipe_steps (recipe_id, step_order, step_type, step_name, duration_days, parameters)
                VALUES (?, ?, ?, ?, ?, ?)
            """, recipe_id_pork, step_order, recipe_id_pork, step_order, step_type, step_name, duration, params)
        
        # Recipe 6: Пластина яловичина (Beef plate)
        cursor.execute("""
            IF NOT EXISTS (SELECT 1 FROM recipes WHERE name = 'Пластина яловичина вагова')
            BEGIN
                INSERT INTO recipes (name, target_product_id, expected_yield_min, expected_yield_max, description)
                VALUES ('Пластина яловичина вагова', 
                       (SELECT id FROM nomenclature WHERE name = 'Яловичина вищій ґатунок'),
                       53.0, 56.0, 
                       'Яловича пластина')
            END
        """)
        
        recipe_id_plate = cursor.execute("SELECT id FROM recipes WHERE name = 'Пластина яловичина вагова'").fetchone()[0]
        
        steps_plate = [
            (1, 'trim', 'Обрізка та підготовка', 0, json.dumps({'trim_percent_min': 0, 'trim_percent_max': 0})),
            (2, 'marinade', 'Виготовлення маринаду', 0, json.dumps({'type': 'beef_plate_marinade'})),
            (3, 'vacuum', 'Вакуумна фасовка та маринування', 6, json.dumps({'package_weight': 3, 'marinate_days_min': 4, 'marinate_days_max': 6})),
            (4, 'press', 'Пресування', 1, json.dumps({'press_number': 1})),
            (5, 'dry', 'Сушка', 3, json.dumps({'days_min': 2, 'days_max': 3}))
        ]
        
        for step_order, step_type, step_name, duration, params in steps_plate:
            cursor.execute("""
                IF NOT EXISTS (SELECT 1 FROM recipe_steps WHERE recipe_id = ? AND step_order = ?)
                INSERT INTO recipe_steps (recipe_id, step_order, step_type, step_name, duration_days, parameters)
                VALUES (?, ?, ?, ?, ?, ?)
            """, recipe_id_plate, step_order, recipe_id_plate, step_order, step_type, step_name, duration, params)
        
        # Recipe 7: Суджук (Sujuk)
        cursor.execute("""
            IF NOT EXISTS (SELECT 1 FROM recipes WHERE name = 'Суджук ваговий')
            BEGIN
                INSERT INTO recipes (name, target_product_id, expected_yield_min, expected_yield_max, description)
                VALUES ('Суджук ваговий', 
                       (SELECT id FROM nomenclature WHERE name = 'Яловичина другий ґатунок'),
                       60.0, 62.0, 
                       'Суджук ваговий')
            END
        """)
        
        recipe_id_sujuk = cursor.execute("SELECT id FROM recipes WHERE name = 'Суджук ваговий'").fetchone()[0]
        
        steps_sujuk = [
            (1, 'trim', 'Підготовка м\'яса', 0, json.dumps({'meat_types': ['high_grade', 'small_pieces', 'goulash', 'first_grade']})),
            (2, 'marinade_spices', 'Замішування зі специями', 2, json.dumps({'marinate_days': 2})),
            (3, 'grind', 'Помол м\'яса', 0, json.dumps({'grind_type': 'fine'})),
            (4, 'massage', 'Масажер з водою та барвником', 0, json.dumps({'water_per_100kg': 15, 'dye_per_100kg': 0.25})),
            (5, 'stuff', 'Заправка в кишку', 0, json.dumps({'casing_options': [{'length': 93, 'diameter': '48+', 'capacity': 100}, {'length': 65, 'diameter': '53+', 'capacity': 100}]})),
            (6, 'dry', 'Сушка 1', 3, json.dumps({'days': 3})),
            (7, 'press', 'Прес 1', 1, json.dumps({'press_number': 1})),
            (8, 'dry', 'Сушка 2', 2, json.dumps({'days_min': 1, 'days_max': 2})),
            (9, 'press', 'Прес 2', 1, json.dumps({'press_number': 2})),
            (10, 'dry', 'Сушка фінальна', 4, json.dumps({'days_min': 3, 'days_max': 4}))
        ]
        
        for step_order, step_type, step_name, duration, params in steps_sujuk:
            cursor.execute("""
                IF NOT EXISTS (SELECT 1 FROM recipe_steps WHERE recipe_id = ? AND step_order = ?)
                INSERT INTO recipe_steps (recipe_id, step_order, step_type, step_name, duration_days, parameters)
                VALUES (?, ?, ?, ?, ?, ?)
            """, recipe_id_sujuk, step_order, recipe_id_sujuk, step_order, step_type, step_name, duration, params)
        
        # Recipe 8: Махан (Makhan)
        cursor.execute("""
            IF NOT EXISTS (SELECT 1 FROM recipes WHERE name = 'Махан ваговий')
            BEGIN
                INSERT INTO recipes (name, target_product_id, expected_yield_min, expected_yield_max, description)
                VALUES ('Махан ваговий', 
                       (SELECT id FROM nomenclature WHERE name = 'Конина перший ґатунок'),
                       60.0, 66.0, 
                       'Махан ваговий')
            END
        """)
        
        recipe_id_makhan = cursor.execute("SELECT id FROM recipes WHERE name = 'Махан ваговий'").fetchone()[0]
        
        steps_makhan = [
            (1, 'trim', 'Підготовка конини', 0, json.dumps({'includes': ['first_grade', 'trim', 'fat_10_percent', 'goulash']})),
            (2, 'marinade_first', 'Перший маринад та масажер', 5, json.dumps({'marinate_days': 5, 'cold_storage': True})),
            (3, 'marinade_second', 'Другий маринад з гусарською', 0, json.dumps({'add_gusarska': True})),
            (4, 'stuff', 'Заправка в кишку/оболонку', 0, json.dumps({'no_grinding': True})),
            (5, 'cure', 'В\'ялення в холоді', 10, json.dumps({'days': 10})),
            (6, 'dry', 'Сушка', 10, json.dumps({'days': 10}))
        ]
        
        for step_order, step_type, step_name, duration, params in steps_makhan:
            cursor.execute("""
                IF NOT EXISTS (SELECT 1 FROM recipe_steps WHERE recipe_id = ? AND step_order = ?)
                INSERT INTO recipe_steps (recipe_id, step_order, step_type, step_name, duration_days, parameters)
                VALUES (?, ?, ?, ?, ?, ?)
            """, recipe_id_makhan, step_order, recipe_id_makhan, step_order, step_type, step_name, duration, params)
        
        conn.commit()
        print("✅ Recipes seeded successfully")

if __name__ == "__main__":
    seed_recipes()
