"""
Оновлення назв рецептів для відповідності номенклатурі
"""
from database import get_db_connection
from dotenv import load_dotenv

load_dotenv()

def update_recipe_names():
    print("="*80)
    print("ОНОВЛЕННЯ НАЗВ РЕЦЕПТІВ ВИРОБНИЦТВА")
    print("="*80)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Оновлення назв рецептів щоб співпадали з target product
        updates = [
            (3, "Конина", "Бастурма з конини → Конина"),
            (8, "Суджук", "Суджук ваговий → Суджук"),
            (9, "Махан", "Махан ваговий → Махан"),
        ]
        
        print("\nОНОВЛЕННЯ НАЗВ:")
        for recipe_id, new_name, description in updates:
            # Перевірка поточної назви
            cursor.execute("SELECT name FROM recipes WHERE id = ?", recipe_id)
            current = cursor.fetchone()
            
            if current:
                print(f"\n  Recipe {recipe_id}: {description}")
                print(f"    Було: '{current[0]}'")
                print(f"    Стане: '{new_name}'")
                
                # Оновлення
                cursor.execute("""
                    UPDATE recipes
                    SET name = ?
                    WHERE id = ?
                """, new_name, recipe_id)
        
        conn.commit()
        print("\n✅ Оновлення виконано!")
        
        # Перевірка результату
        print("\n" + "="*80)
        print("ПЕРЕВІРКА РЕЗУЛЬТАТУ:")
        print("="*80)
        
        cursor.execute("""
            SELECT r.id, r.name, n.name as target_name
            FROM recipes r
            LEFT JOIN nomenclature n ON r.target_product_id = n.id
            ORDER BY r.id
        """)
        
        recipes = cursor.fetchall()
        
        print("\nОНОВЛЕНІ РЕЦЕПТИ:")
        for recipe_id, recipe_name, target_name in recipes:
            match = "✅" if recipe_name.lower() in target_name.lower() or target_name.lower() in recipe_name.lower() else "⚠️ "
            print(f"  {match} ID {recipe_id}: {recipe_name} → {target_name}")

if __name__ == "__main__":
    try:
        update_recipe_names()
    except Exception as e:
        print(f"\n❌ ПОМИЛКА: {e}")
        import traceback
        traceback.print_exc()
