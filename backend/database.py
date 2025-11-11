import pyodbc
import os
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

MSSQL_SERVER = os.getenv("MSSQL_SERVER")
MSSQL_DATABASE = os.getenv("MSSQL_DATABASE")
MSSQL_USER = os.getenv("MSSQL_USER")
MSSQL_PASSWORD = os.getenv("MSSQL_PASSWORD")
MSSQL_DRIVER = os.getenv("MSSQL_DRIVER", "ODBC Driver 18 for SQL Server")

# Connection string for MS SQL Server
CONNECTION_STRING = (
    f"DRIVER={{{MSSQL_DRIVER}}};"
    f"SERVER={MSSQL_SERVER};"
    f"DATABASE={MSSQL_DATABASE};"
    f"UID={MSSQL_USER};"
    f"PWD={MSSQL_PASSWORD};"
    f"Encrypt=no;"
    f"TrustServerCertificate=yes;"
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
        
        # Create inventory_sessions table
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='inventory_sessions' AND xtype='U')
        CREATE TABLE inventory_sessions (
            id INT IDENTITY(1,1) PRIMARY KEY,
            session_type NVARCHAR(50) NOT NULL,
            status NVARCHAR(50) NOT NULL DEFAULT 'in_progress',
            started_at DATETIME2 DEFAULT GETUTCDATE(),
            completed_at DATETIME2,
            idempotency_key NVARCHAR(255) NOT NULL,
            metadata NVARCHAR(MAX),
            CONSTRAINT UQ_inventory_idempotency UNIQUE(idempotency_key)
        )
        """)
        
        # Create inventory_items table
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='inventory_items' AND xtype='U')
        CREATE TABLE inventory_items (
            id INT IDENTITY(1,1) PRIMARY KEY,
            session_id INT NOT NULL,
            nomenclature_id INT NOT NULL,
            system_quantity DECIMAL(18, 6) NOT NULL,
            actual_quantity DECIMAL(18, 6) NOT NULL,
            difference DECIMAL(18, 6) NOT NULL,
            created_at DATETIME2 DEFAULT GETUTCDATE(),
            FOREIGN KEY (session_id) REFERENCES inventory_sessions(id),
            FOREIGN KEY (nomenclature_id) REFERENCES nomenclature(id)
        )
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
        
        conn.commit()
        print("Database schema initialized successfully")
