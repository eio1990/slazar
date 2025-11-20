"""
Migration: Cleanup trim columns and replace 'сорт' with 'ґатунок'
"""
import pyodbc
from database import get_db_connection
from dotenv import load_dotenv

load_dotenv()

def migrate():
    """Execute cleanup migrations"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        print("🔄 Starting migrations...")
        
        # Task 11: Remove trim columns from batches table
        print("\n1️⃣ Removing trim columns from batches table...")
        try:
            # Check if columns exist
            cursor.execute("""
                SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'batches' AND COLUMN_NAME IN ('trim_waste', 'trim_returned')
            """)
            trim_columns = [row[0] for row in cursor.fetchall()]
            
            if trim_columns:
                print(f"   Found trim columns: {trim_columns}")
                for col in trim_columns:
                    cursor.execute(f"ALTER TABLE batches DROP COLUMN {col}")
                    print(f"   ✅ Dropped column: {col}")
                conn.commit()
            else:
                print("   ℹ️  No trim columns found (already removed)")
        except Exception as e:
            print(f"   ⚠️  Error with trim columns: {e}")
            conn.rollback()
        
        # Task 12: Replace 'сорт' with 'ґатунок' in all tables
        print("\n2️⃣ Replacing 'сорт' with 'ґатунок'...")
        
        # Get all text columns that might contain 'сорт'
        cursor.execute("""
            SELECT TABLE_NAME, COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE DATA_TYPE IN ('varchar', 'nvarchar', 'text', 'ntext')
            AND TABLE_NAME IN ('nomenclature', 'recipes', 'butchery_recipes', 'nomenclature_categories')
        """)
        
        text_columns = cursor.fetchall()
        updated_count = 0
        
        for table_name, column_name in text_columns:
            try:
                # Update records containing 'сорт'
                cursor.execute(f"""
                    UPDATE {table_name}
                    SET {column_name} = REPLACE({column_name}, N'сорт', N'ґатунок')
                    WHERE {column_name} LIKE N'%сорт%'
                """)
                rows_affected = cursor.rowcount
                if rows_affected > 0:
                    print(f"   ✅ Updated {rows_affected} rows in {table_name}.{column_name}")
                    updated_count += rows_affected
            except Exception as e:
                print(f"   ⚠️  Error updating {table_name}.{column_name}: {e}")
        
        conn.commit()
        print(f"\n   Total rows updated: {updated_count}")
        
        print("\n✅ All migrations completed successfully!")

if __name__ == "__main__":
    migrate()
