import pyodbc
import os
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

# Database connection settings
# NOTE: To allow connections from other networks, ensure MS SQL Server is configured to:
# 1. Accept remote connections (SQL Server Configuration Manager -> SQL Server Network Configuration -> TCP/IP enabled)
# 2. Firewall allows port 14330 for incoming connections
# 3. SQL Server Authentication is enabled (not just Windows Authentication)
# 4. User llm_user has proper permissions
MSSQL_SERVER = os.getenv("MSSQL_SERVER")
MSSQL_DATABASE = os.getenv("MSSQL_DATABASE")
MSSQL_USER = os.getenv("MSSQL_USER")
MSSQL_PASSWORD = os.getenv("MSSQL_PASSWORD")
MSSQL_DRIVER = os.getenv("MSSQL_DRIVER", "ODBC Driver 18 for SQL Server")

# Connection string for MS SQL Server
# Added charset=UTF-8 to properly handle Cyrillic characters
CONNECTION_STRING = (
    f"DRIVER={{{MSSQL_DRIVER}}};"
    f"SERVER={MSSQL_SERVER};"
    f"DATABASE={MSSQL_DATABASE};"
    f"UID={MSSQL_USER};"
    f"PWD={MSSQL_PASSWORD};"
    f"Encrypt=no;"
    f"TrustServerCertificate=yes;"
    f"LoginTimeout=30;"  # Increase timeout to 30 seconds
    f"Timeout=30;"
    f"charset=UTF-8;"
)

@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = None
    try:
        conn = pyodbc.connect(CONNECTION_STRING)
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()

def get_db_cursor(conn):
    """Get cursor from connection"""
    return conn.cursor()

def init_database():
    """Initialize database schema"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Create nomenclature table
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='nomenclature' AND xtype='U')
        CREATE TABLE nomenclature (
            id INT IDENTITY(1,1) PRIMARY KEY,
            name NVARCHAR(255) NOT NULL,
            category NVARCHAR(100) NOT NULL,
            unit NVARCHAR(50) NOT NULL,
            precision_digits INT NOT NULL DEFAULT 2,
            created_at DATETIME2 DEFAULT GETUTCDATE(),
            updated_at DATETIME2 DEFAULT GETUTCDATE(),
            CONSTRAINT UQ_nomenclature_name UNIQUE(name)
        )
        """)
        
        # Create stock_movements table
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='stock_movements' AND xtype='U')
        CREATE TABLE stock_movements (
            id INT IDENTITY(1,1) PRIMARY KEY,
            nomenclature_id INT NOT NULL,
            operation_type NVARCHAR(50) NOT NULL,
            quantity DECIMAL(18, 6) NOT NULL,
            balance_after DECIMAL(18, 6) NOT NULL,
            price_per_unit DECIMAL(18, 2),
            source_operation_type NVARCHAR(50),
            source_operation_id NVARCHAR(100),
            parent_movement_id INT,
            idempotency_key NVARCHAR(255) NOT NULL,
            metadata NVARCHAR(MAX),
            operation_date DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
            created_at DATETIME2 DEFAULT GETUTCDATE(),
            FOREIGN KEY (nomenclature_id) REFERENCES nomenclature(id),
            FOREIGN KEY (parent_movement_id) REFERENCES stock_movements(id),
            CONSTRAINT UQ_idempotency_key UNIQUE(idempotency_key)
        )
        """)
        
        # Add columns if they don't exist (for existing tables)
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.columns 
                      WHERE object_id = OBJECT_ID('stock_movements') 
                      AND name = 'price_per_unit')
        BEGIN
            ALTER TABLE stock_movements ADD price_per_unit DECIMAL(18, 2)
        END
        
        IF NOT EXISTS (SELECT * FROM sys.columns 
                      WHERE object_id = OBJECT_ID('stock_movements') 
                      AND name = 'source_operation_type')
        BEGIN
            ALTER TABLE stock_movements ADD source_operation_type NVARCHAR(50)
        END
        
        IF NOT EXISTS (SELECT * FROM sys.columns 
                      WHERE object_id = OBJECT_ID('stock_movements') 
                      AND name = 'source_operation_id')
        BEGIN
            ALTER TABLE stock_movements ADD source_operation_id NVARCHAR(100)
        END
        
        IF NOT EXISTS (SELECT * FROM sys.columns 
                      WHERE object_id = OBJECT_ID('stock_movements') 
                      AND name = 'parent_movement_id')
        BEGIN
            ALTER TABLE stock_movements ADD parent_movement_id INT
        END
        """)
        
        # Create index on operation_date for faster queries
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='IX_stock_movements_date' AND object_id = OBJECT_ID('stock_movements'))
        CREATE INDEX IX_stock_movements_date ON stock_movements(operation_date DESC)
        """)
        
        # Create stock_balances table
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='stock_balances' AND xtype='U')
        CREATE TABLE stock_balances (
            nomenclature_id INT PRIMARY KEY,
            quantity DECIMAL(18, 6) NOT NULL DEFAULT 0,
            last_updated DATETIME2 DEFAULT GETUTCDATE(),
            FOREIGN KEY (nomenclature_id) REFERENCES nomenclature(id)
        )
        """)
        
        # ========== INVENTORY MODULE TABLES ==========

        # Create inventory_sessions table (сесії інвентаризації)
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='inventory_sessions' AND xtype='U')
        CREATE TABLE inventory_sessions (
            id INT IDENTITY(1,1) PRIMARY KEY,
            session_number NVARCHAR(50) NOT NULL,
            session_type NVARCHAR(50) NOT NULL,
            status NVARCHAR(50) NOT NULL DEFAULT 'in_progress',
            started_at DATETIME2 DEFAULT GETUTCDATE(),
            completed_at DATETIME2,
            idempotency_key NVARCHAR(255) NOT NULL,
            metadata NVARCHAR(MAX),
            CONSTRAINT UQ_inventory_session_number UNIQUE(session_number),
            CONSTRAINT UQ_inventory_idempotency UNIQUE(idempotency_key)
        )
        """)

        # Create inventory_snapshot table (snapshot залишків на момент початку інвентаризації)
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='inventory_snapshot' AND xtype='U')
        CREATE TABLE inventory_snapshot (
            id INT IDENTITY(1,1) PRIMARY KEY,
            session_id INT NOT NULL,
            nomenclature_id INT NOT NULL,
            snapshot_quantity DECIMAL(18, 6) NOT NULL,
            snapshot_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
            FOREIGN KEY (session_id) REFERENCES inventory_sessions(id) ON DELETE CASCADE,
            FOREIGN KEY (nomenclature_id) REFERENCES nomenclature(id),
            CONSTRAINT UQ_inventory_snapshot UNIQUE(session_id, nomenclature_id)
        )
        """)

        # Create inventory_items table (підраховані позиції з різницями)
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='inventory_items' AND xtype='U')
        CREATE TABLE inventory_items (
            id INT IDENTITY(1,1) PRIMARY KEY,
            session_id INT NOT NULL,
            nomenclature_id INT NOT NULL,
            system_quantity DECIMAL(18, 6) NOT NULL,
            actual_quantity DECIMAL(18, 6),
            difference DECIMAL(18, 6),
            difference_percent DECIMAL(18, 2),
            status NVARCHAR(50) NOT NULL DEFAULT 'pending',
            requires_verification BIT DEFAULT 0,
            counted_at DATETIME2,
            notes NVARCHAR(MAX),
            created_at DATETIME2 DEFAULT GETUTCDATE(),
            FOREIGN KEY (session_id) REFERENCES inventory_sessions(id) ON DELETE CASCADE,
            FOREIGN KEY (nomenclature_id) REFERENCES nomenclature(id),
            CONSTRAINT UQ_inventory_item UNIQUE(session_id, nomenclature_id)
        )
        """)

        # Add session_number column if missing (для старих таблиць)
        cursor.execute("""
        IF EXISTS (SELECT * FROM sysobjects WHERE name='inventory_sessions' AND xtype='U')
        BEGIN
            IF NOT EXISTS (SELECT * FROM sys.columns
                          WHERE object_id = OBJECT_ID('inventory_sessions')
                          AND name = 'session_number')
            BEGIN
                ALTER TABLE inventory_sessions ADD session_number NVARCHAR(50)
            END

            IF NOT EXISTS (SELECT * FROM sys.columns
                          WHERE object_id = OBJECT_ID('inventory_items')
                          AND name = 'difference_percent')
            BEGIN
                ALTER TABLE inventory_items ADD difference_percent DECIMAL(18, 2)
            END

            IF NOT EXISTS (SELECT * FROM sys.columns
                          WHERE object_id = OBJECT_ID('inventory_items')
                          AND name = 'status')
            BEGIN
                ALTER TABLE inventory_items ADD status NVARCHAR(50) DEFAULT 'pending'
            END

            IF NOT EXISTS (SELECT * FROM sys.columns
                          WHERE object_id = OBJECT_ID('inventory_items')
                          AND name = 'requires_verification')
            BEGIN
                ALTER TABLE inventory_items ADD requires_verification BIT DEFAULT 0
            END

            IF NOT EXISTS (SELECT * FROM sys.columns
                          WHERE object_id = OBJECT_ID('inventory_items')
                          AND name = 'counted_at')
            BEGIN
                ALTER TABLE inventory_items ADD counted_at DATETIME2
            END

            IF NOT EXISTS (SELECT * FROM sys.columns
                          WHERE object_id = OBJECT_ID('inventory_items')
                          AND name = 'notes')
            BEGIN
                ALTER TABLE inventory_items ADD notes NVARCHAR(MAX)
            END
        END
        """)
        
        # Create recipes table
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='recipes' AND xtype='U')
        CREATE TABLE recipes (
            id INT IDENTITY(1,1) PRIMARY KEY,
            name NVARCHAR(255) NOT NULL,
            target_product_id INT NOT NULL,
            expected_yield_min DECIMAL(5, 2),
            expected_yield_max DECIMAL(5, 2),
            description NVARCHAR(MAX),
            created_at DATETIME2 DEFAULT GETUTCDATE(),
            updated_at DATETIME2 DEFAULT GETUTCDATE(),
            FOREIGN KEY (target_product_id) REFERENCES nomenclature(id),
            CONSTRAINT UQ_recipe_name UNIQUE(name)
        )
        """)
        
        # Create recipe_ingredients table (raw materials)
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='recipe_ingredients' AND xtype='U')
        CREATE TABLE recipe_ingredients (
            id INT IDENTITY(1,1) PRIMARY KEY,
            recipe_id INT NOT NULL,
            nomenclature_id INT NOT NULL,
            quantity_per_100kg DECIMAL(18, 6),
            is_optional BIT DEFAULT 0,
            notes NVARCHAR(MAX),
            created_at DATETIME2 DEFAULT GETUTCDATE(),
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
            FOREIGN KEY (nomenclature_id) REFERENCES nomenclature(id)
        )
        """)
        
        # Create recipe_spices table
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='recipe_spices' AND xtype='U')
        CREATE TABLE recipe_spices (
            id INT IDENTITY(1,1) PRIMARY KEY,
            recipe_id INT NOT NULL,
            nomenclature_id INT NOT NULL,
            quantity_per_100kg DECIMAL(18, 6),
            is_fenugreek BIT DEFAULT 0,
            notes NVARCHAR(MAX),
            created_at DATETIME2 DEFAULT GETUTCDATE(),
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
            FOREIGN KEY (nomenclature_id) REFERENCES nomenclature(id)
        )
        """)
        
        # Create recipe_steps table
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='recipe_steps' AND xtype='U')
        CREATE TABLE recipe_steps (
            id INT IDENTITY(1,1) PRIMARY KEY,
            recipe_id INT NOT NULL,
            step_order INT NOT NULL,
            step_type NVARCHAR(50) NOT NULL,
            step_name NVARCHAR(255) NOT NULL,
            duration_days DECIMAL(5, 2),
            parameters NVARCHAR(MAX),
            description NVARCHAR(MAX),
            created_at DATETIME2 DEFAULT GETUTCDATE(),
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
        )
        """)
        
        # Create batches table (production batches)
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='batches' AND xtype='U')
        CREATE TABLE batches (
            id INT IDENTITY(1,1) PRIMARY KEY,
            batch_number NVARCHAR(100) NOT NULL,
            recipe_id INT NOT NULL,
            status NVARCHAR(50) NOT NULL DEFAULT 'created',
            current_step INT DEFAULT 0,
            started_at DATETIME2 DEFAULT GETUTCDATE(),
            completed_at DATETIME2,
            initial_weight DECIMAL(18, 6),
            final_weight DECIMAL(18, 6),
            trim_waste DECIMAL(18, 6),
            trim_returned BIT DEFAULT 0,
            operator_notes NVARCHAR(MAX),
            created_at DATETIME2 DEFAULT GETUTCDATE(),
            updated_at DATETIME2 DEFAULT GETUTCDATE(),
            FOREIGN KEY (recipe_id) REFERENCES recipes(id),
            CONSTRAINT UQ_batch_number UNIQUE(batch_number)
        )
        """)
        
        # Create batch_operations table
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='batch_operations' AND xtype='U')
        CREATE TABLE batch_operations (
            id INT IDENTITY(1,1) PRIMARY KEY,
            batch_id INT NOT NULL,
            step_id INT NOT NULL,
            operation_type NVARCHAR(50) NOT NULL,
            status NVARCHAR(50) NOT NULL DEFAULT 'in_progress',
            started_at DATETIME2 DEFAULT GETUTCDATE(),
            completed_at DATETIME2,
            weight_before DECIMAL(18, 6),
            weight_after DECIMAL(18, 6),
            parameters NVARCHAR(MAX),
            notes NVARCHAR(MAX),
            idempotency_key NVARCHAR(255) NOT NULL,
            created_at DATETIME2 DEFAULT GETUTCDATE(),
            FOREIGN KEY (batch_id) REFERENCES batches(id) ON DELETE CASCADE,
            FOREIGN KEY (step_id) REFERENCES recipe_steps(id),
            CONSTRAINT UQ_batch_operation_idempotency UNIQUE(idempotency_key)
        )
        """)
        
        # Create batch_mix_production table
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='batch_mix_production' AND xtype='U')
        CREATE TABLE batch_mix_production (
            id INT IDENTITY(1,1) PRIMARY KEY,
            batch_id INT NOT NULL,
            mix_nomenclature_id INT NOT NULL,
            produced_quantity DECIMAL(18, 6) NOT NULL DEFAULT 0,
            used_quantity DECIMAL(18, 6) NOT NULL DEFAULT 0,
            leftover_quantity DECIMAL(18, 6) NOT NULL DEFAULT 0,
            warehouse_mix_used DECIMAL(18, 6) NOT NULL DEFAULT 0,
            idempotency_key NVARCHAR(255) NOT NULL,
            created_at DATETIME2 DEFAULT GETUTCDATE(),
            FOREIGN KEY (batch_id) REFERENCES batches(id) ON DELETE CASCADE,
            FOREIGN KEY (mix_nomenclature_id) REFERENCES nomenclature(id),
            CONSTRAINT UQ_batch_mix_idempotency UNIQUE(idempotency_key)
        )
        """)
        
        # Create batch_materials table (track all materials used in batch)
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='batch_materials' AND xtype='U')
        CREATE TABLE batch_materials (
            id INT IDENTITY(1,1) PRIMARY KEY,
            batch_id INT NOT NULL,
            nomenclature_id INT NOT NULL,
            material_type NVARCHAR(50) NOT NULL,
            quantity_used DECIMAL(18, 6) NOT NULL,
            movement_id INT,
            notes NVARCHAR(MAX),
            created_at DATETIME2 DEFAULT GETUTCDATE(),
            FOREIGN KEY (batch_id) REFERENCES batches(id) ON DELETE CASCADE,
            FOREIGN KEY (nomenclature_id) REFERENCES nomenclature(id),
            FOREIGN KEY (movement_id) REFERENCES stock_movements(id)
        )
        """)
        
        # ========== PACKAGING MODULE TABLES ==========
        
        # Create packaging_recipes table (нормы расхода материалов для фасовки)
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='packaging_recipes' AND xtype='U')
        CREATE TABLE packaging_recipes (
            id INT IDENTITY(1,1) PRIMARY KEY,
            source_product_id INT NOT NULL,
            target_product_id INT NOT NULL,
            packaging_type NVARCHAR(50) NOT NULL,
            target_weight_grams INT NOT NULL,
            is_active BIT NOT NULL DEFAULT 1,
            notes NVARCHAR(MAX),
            created_at DATETIME2 DEFAULT GETUTCDATE(),
            updated_at DATETIME2 DEFAULT GETUTCDATE(),
            FOREIGN KEY (source_product_id) REFERENCES nomenclature(id),
            FOREIGN KEY (target_product_id) REFERENCES nomenclature(id),
            CONSTRAINT UQ_packaging_recipe UNIQUE(source_product_id, target_product_id, packaging_type)
        )
        """)
        
        # Create packaging_recipe_materials table (материалы для конкретного рецепта фасовки)
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='packaging_recipe_materials' AND xtype='U')
        CREATE TABLE packaging_recipe_materials (
            id INT IDENTITY(1,1) PRIMARY KEY,
            recipe_id INT NOT NULL,
            material_id INT NOT NULL,
            quantity_per_unit DECIMAL(18, 6) NOT NULL,
            rounding_precision DECIMAL(18, 6),
            material_type NVARCHAR(50) NOT NULL,
            notes NVARCHAR(MAX),
            created_at DATETIME2 DEFAULT GETUTCDATE(),
            FOREIGN KEY (recipe_id) REFERENCES packaging_recipes(id) ON DELETE CASCADE,
            FOREIGN KEY (material_id) REFERENCES nomenclature(id)
        )
        """)
        
        # Create packaging_batches table (партии фасовки)
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='packaging_batches' AND xtype='U')
        CREATE TABLE packaging_batches (
            id INT IDENTITY(1,1) PRIMARY KEY,
            batch_number NVARCHAR(50) NOT NULL,
            recipe_id INT NOT NULL,
            source_product_id INT NOT NULL,
            target_product_id INT NOT NULL,
            status NVARCHAR(50) NOT NULL DEFAULT 'in_progress',
            planned_quantity INT,
            source_weight_taken DECIMAL(18, 6) NOT NULL,
            actual_packed_quantity INT DEFAULT 0,
            actual_source_used DECIMAL(18, 6) DEFAULT 0,
            waste_quantity DECIMAL(18, 6) DEFAULT 0,
            started_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
            completed_at DATETIME2,
            operator_notes NVARCHAR(MAX),
            created_at DATETIME2 DEFAULT GETUTCDATE(),
            updated_at DATETIME2 DEFAULT GETUTCDATE(),
            FOREIGN KEY (recipe_id) REFERENCES packaging_recipes(id),
            FOREIGN KEY (source_product_id) REFERENCES nomenclature(id),
            FOREIGN KEY (target_product_id) REFERENCES nomenclature(id),
            CONSTRAINT UQ_packaging_batch_number UNIQUE(batch_number)
        )
        """)
        
        # Create packaging_operations table (операции фасовки в рамках партии)
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='packaging_operations' AND xtype='U')
        CREATE TABLE packaging_operations (
            id INT IDENTITY(1,1) PRIMARY KEY,
            batch_id INT NOT NULL,
            operation_type NVARCHAR(50) NOT NULL,
            packed_quantity INT NOT NULL,
            source_used DECIMAL(18, 6) NOT NULL,
            waste_quantity DECIMAL(18, 6) DEFAULT 0,
            notes NVARCHAR(MAX),
            idempotency_key NVARCHAR(255) NOT NULL,
            created_at DATETIME2 DEFAULT GETUTCDATE(),
            FOREIGN KEY (batch_id) REFERENCES packaging_batches(id) ON DELETE CASCADE,
            CONSTRAINT UQ_packaging_operation_key UNIQUE(idempotency_key)
        )
        """)
        
        # Create packaging_material_consumption table (расход материалов в операциях)
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='packaging_material_consumption' AND xtype='U')
        CREATE TABLE packaging_material_consumption (
            id INT IDENTITY(1,1) PRIMARY KEY,
            operation_id INT NOT NULL,
            material_id INT NOT NULL,
            quantity_used DECIMAL(18, 6) NOT NULL,
            movement_id INT,
            notes NVARCHAR(MAX),
            created_at DATETIME2 DEFAULT GETUTCDATE(),
            FOREIGN KEY (operation_id) REFERENCES packaging_operations(id) ON DELETE CASCADE,
            FOREIGN KEY (material_id) REFERENCES nomenclature(id),
            FOREIGN KEY (movement_id) REFERENCES stock_movements(id)
        )
        """)

        # ========== COSTING MODULE TABLES ==========

        # Create nomenclature_costs table (середньозважена собівартість)
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='nomenclature_costs' AND xtype='U')
        CREATE TABLE nomenclature_costs (
            nomenclature_id INT PRIMARY KEY,
            weighted_avg_cost DECIMAL(18, 4) NOT NULL DEFAULT 0,
            last_purchase_cost DECIMAL(18, 4),
            total_quantity DECIMAL(18, 6) NOT NULL DEFAULT 0,
            total_value DECIMAL(18, 4) NOT NULL DEFAULT 0,
            last_updated DATETIME2 DEFAULT GETUTCDATE(),
            FOREIGN KEY (nomenclature_id) REFERENCES nomenclature(id)
        )
        """)

        # Create butchery_operation_costs table (калькуляція розділки зі стеком)
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='butchery_operation_costs' AND xtype='U')
        CREATE TABLE butchery_operation_costs (
            id INT IDENTITY(1,1) PRIMARY KEY,
            operation_id INT NOT NULL UNIQUE,

            -- Вхідна сировина
            input_nomenclature_id INT NOT NULL,
            input_weight DECIMAL(18, 6) NOT NULL,
            input_cost_per_kg DECIMAL(18, 4) NOT NULL,
            input_total_cost DECIMAL(18, 4) NOT NULL,

            -- Вихід
            total_output_weight DECIMAL(18, 6) NOT NULL,      -- Сума полуфабрикатів + відходів
            semifinished_weight DECIMAL(18, 6) NOT NULL,      -- Тільки полуфабрикати (без відходів)
            waste_weight DECIMAL(18, 6) NOT NULL,             -- Відходи

            -- Стек (усушка/вихід води)
            shrinkage_weight DECIMAL(18, 6) NOT NULL,         -- input_weight - total_output_weight
            shrinkage_percent DECIMAL(5, 2) NOT NULL,

            -- Скоригована собівартість
            adjusted_cost_per_kg DECIMAL(18, 4) NOT NULL,     -- З урахуванням стека

            calculated_at DATETIME2 DEFAULT GETUTCDATE(),

            FOREIGN KEY (input_nomenclature_id) REFERENCES nomenclature(id)
        )
        """)

        # Create batch_costs table (калькуляція виробництва)
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='batch_costs' AND xtype='U')
        CREATE TABLE batch_costs (
            batch_id INT NOT NULL UNIQUE,

            -- Собівартість сировини та матеріалів
            raw_materials_cost DECIMAL(18, 4) NOT NULL DEFAULT 0,
            salt_cost DECIMAL(18, 4) NOT NULL DEFAULT 0,
            spices_cost DECIMAL(18, 4) NOT NULL DEFAULT 0,
            casings_cost DECIMAL(18, 4) NOT NULL DEFAULT 0,
            other_materials_cost DECIMAL(18, 4) NOT NULL DEFAULT 0,

            -- Підсумки
            total_cost DECIMAL(18, 4) NOT NULL DEFAULT 0,
            final_weight DECIMAL(18, 6) NOT NULL DEFAULT 0,
            cost_per_kg DECIMAL(18, 4) NOT NULL DEFAULT 0,

            -- Втрати
            shrinkage_weight DECIMAL(18, 6) NOT NULL DEFAULT 0,
            shrinkage_percent DECIMAL(5, 2) NOT NULL DEFAULT 0,

            calculated_at DATETIME2 DEFAULT GETUTCDATE(),
            updated_at DATETIME2 DEFAULT GETUTCDATE(),

            FOREIGN KEY (batch_id) REFERENCES batches(id) ON DELETE CASCADE
        )
        """)

        # Create packaging_batch_costs table (калькуляція фасування)
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='packaging_batch_costs' AND xtype='U')
        CREATE TABLE packaging_batch_costs (
            packaging_batch_id INT NOT NULL UNIQUE,

            -- Собівартість вагової продукції
            source_product_cost DECIMAL(18, 4) NOT NULL DEFAULT 0,
            source_product_total DECIMAL(18, 4) NOT NULL DEFAULT 0,

            -- Собівартість матеріалів
            packaging_materials_cost DECIMAL(18, 4) NOT NULL DEFAULT 0,

            -- Підсумки
            total_cost DECIMAL(18, 4) NOT NULL DEFAULT 0,
            packed_quantity INT NOT NULL DEFAULT 0,
            cost_per_unit DECIMAL(18, 4) NOT NULL DEFAULT 0,

            -- Втрати
            waste_weight DECIMAL(18, 6) NOT NULL DEFAULT 0,
            waste_cost DECIMAL(18, 4) NOT NULL DEFAULT 0,

            calculated_at DATETIME2 DEFAULT GETUTCDATE(),
            updated_at DATETIME2 DEFAULT GETUTCDATE(),

            FOREIGN KEY (packaging_batch_id) REFERENCES packaging_batches(id) ON DELETE CASCADE
        )
        """)

        # Add cost columns to stock_movements if not exist
        cursor.execute("""
        IF EXISTS (SELECT * FROM sysobjects WHERE name='stock_movements' AND xtype='U')
        BEGIN
            IF NOT EXISTS (SELECT * FROM sys.columns
                          WHERE object_id = OBJECT_ID('stock_movements')
                          AND name = 'cost_per_unit')
            BEGIN
                ALTER TABLE stock_movements ADD cost_per_unit DECIMAL(18, 4)
            END

            IF NOT EXISTS (SELECT * FROM sys.columns
                          WHERE object_id = OBJECT_ID('stock_movements')
                          AND name = 'total_cost')
            BEGIN
                ALTER TABLE stock_movements ADD total_cost DECIMAL(18, 4)
            END
        END
        """)

        conn.commit()
        print("Database schema initialized successfully")
