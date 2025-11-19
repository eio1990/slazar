"""
Міграція: Додавання модуля розділки
- Додати nomenclature_type до nomenclature
- Створити 4 нові таблиці для розділки
"""
import pyodbc
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={os.getenv('MSSQL_SERVER')};"
        f"DATABASE={os.getenv('MSSQL_DATABASE')};"
        f"UID={os.getenv('MSSQL_USER')};"
        f"PWD={os.getenv('MSSQL_PASSWORD')};"
        f"TrustServerCertificate=yes;"
    )
    return pyodbc.connect(conn_str)

def migrate():
    conn = get_connection()
    cursor = conn.cursor()
    
    print("=" * 60)
    print("МІГРАЦІЯ: Додавання модуля розділки")
    print("=" * 60)
    
    # 1. Додати nomenclature_type до nomenclature
    print("\n1. Додавання nomenclature_type до nomenclature...")
    try:
        cursor.execute("""
            IF NOT EXISTS (
                SELECT * FROM sys.columns 
                WHERE object_id = OBJECT_ID('nomenclature') 
                AND name = 'nomenclature_type'
            )
            BEGIN
                ALTER TABLE nomenclature 
                ADD nomenclature_type NVARCHAR(50) DEFAULT 'raw'
            END
        """)
        conn.commit()
        print("   ✅ nomenclature_type додано")
    except Exception as e:
        print(f"   ⚠️ Помилка: {e}")
    
    # 2. Створити таблицю butchery_recipes
    print("\n2. Створення таблиці butchery_recipes...")
    try:
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='butchery_recipes' AND xtype='U')
            CREATE TABLE butchery_recipes (
                id INT IDENTITY PRIMARY KEY,
                name NVARCHAR(200) NOT NULL,
                source_nomenclature_id INT NOT NULL,
                description NVARCHAR(500),
                level INT DEFAULT 1,
                is_active BIT DEFAULT 1,
                created_at DATETIME2 DEFAULT GETUTCDATE(),
                FOREIGN KEY (source_nomenclature_id) REFERENCES nomenclature(id)
            )
        """)
        conn.commit()
        print("   ✅ butchery_recipes створено")
    except Exception as e:
        print(f"   ⚠️ Помилка: {e}")
    
    # 3. Створити таблицю butchery_recipe_outputs
    print("\n3. Створення таблиці butchery_recipe_outputs...")
    try:
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='butchery_recipe_outputs' AND xtype='U')
            CREATE TABLE butchery_recipe_outputs (
                id INT IDENTITY PRIMARY KEY,
                recipe_id INT NOT NULL,
                output_nomenclature_id INT NOT NULL,
                yield_percentage DECIMAL(5,2) NOT NULL,
                is_main_output BIT DEFAULT 0,
                output_type NVARCHAR(50),
                FOREIGN KEY (recipe_id) REFERENCES butchery_recipes(id),
                FOREIGN KEY (output_nomenclature_id) REFERENCES nomenclature(id)
            )
        """)
        conn.commit()
        print("   ✅ butchery_recipe_outputs створено")
    except Exception as e:
        print(f"   ⚠️ Помилка: {e}")
    
    # 4. Створити таблицю butchery_operations
    print("\n4. Створення таблиці butchery_operations...")
    try:
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='butchery_operations' AND xtype='U')
            CREATE TABLE butchery_operations (
                id INT IDENTITY PRIMARY KEY,
                operation_number NVARCHAR(50) UNIQUE NOT NULL,
                recipe_id INT NOT NULL,
                source_nomenclature_id INT NOT NULL,
                input_weight DECIMAL(10,2) NOT NULL,
                status NVARCHAR(50) DEFAULT 'in_progress',
                started_at DATETIME2 DEFAULT GETUTCDATE(),
                completed_at DATETIME2,
                operator_notes NVARCHAR(500),
                idempotency_key NVARCHAR(200) UNIQUE,
                FOREIGN KEY (recipe_id) REFERENCES butchery_recipes(id),
                FOREIGN KEY (source_nomenclature_id) REFERENCES nomenclature(id)
            )
        """)
        conn.commit()
        print("   ✅ butchery_operations створено")
    except Exception as e:
        print(f"   ⚠️ Помилка: {e}")
    
    # 5. Створити таблицю butchery_operation_outputs
    print("\n5. Створення таблиці butchery_operation_outputs...")
    try:
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='butchery_operation_outputs' AND xtype='U')
            CREATE TABLE butchery_operation_outputs (
                id INT IDENTITY PRIMARY KEY,
                operation_id INT NOT NULL,
                output_nomenclature_id INT NOT NULL,
                expected_weight DECIMAL(10,2),
                actual_weight DECIMAL(10,2) NOT NULL,
                notes NVARCHAR(200),
                FOREIGN KEY (operation_id) REFERENCES butchery_operations(id),
                FOREIGN KEY (output_nomenclature_id) REFERENCES nomenclature(id)
            )
        """)
        conn.commit()
        print("   ✅ butchery_operation_outputs створено")
    except Exception as e:
        print(f"   ⚠️ Помилка: {e}")
    
    # 6. Створити індекси
    print("\n6. Створення індексів...")
    try:
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_butchery_ops_status')
            CREATE INDEX idx_butchery_ops_status ON butchery_operations(status)
        """)
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_butchery_outputs_operation')
            CREATE INDEX idx_butchery_outputs_operation ON butchery_operation_outputs(operation_id)
        """)
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_nomenclature_type')
            CREATE INDEX idx_nomenclature_type ON nomenclature(nomenclature_type)
        """)
        conn.commit()
        print("   ✅ Індекси створено")
    except Exception as e:
        print(f"   ⚠️ Помилка: {e}")
    
    print("\n" + "=" * 60)
    print("МІГРАЦІЯ ЗАВЕРШЕНА")
    print("=" * 60)
    
    conn.close()

if __name__ == "__main__":
    migrate()
