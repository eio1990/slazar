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
            created_at DATETIME2 DEFAULT GETDATE(),
            updated_at DATETIME2 DEFAULT GETDATE(),
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
            idempotency_key NVARCHAR(255) NOT NULL,
            metadata NVARCHAR(MAX),
            operation_date DATETIME2 NOT NULL DEFAULT GETDATE(),
            created_at DATETIME2 DEFAULT GETDATE(),
            FOREIGN KEY (nomenclature_id) REFERENCES nomenclature(id),
            CONSTRAINT UQ_idempotency_key UNIQUE(idempotency_key)
        )
        """)
        
        # Add price_per_unit column if it doesn't exist (for existing tables)
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.columns 
                      WHERE object_id = OBJECT_ID('stock_movements') 
                      AND name = 'price_per_unit')
        BEGIN
            ALTER TABLE stock_movements ADD price_per_unit DECIMAL(18, 2)
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
            last_updated DATETIME2 DEFAULT GETDATE(),
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
            started_at DATETIME2 DEFAULT GETDATE(),
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
            created_at DATETIME2 DEFAULT GETDATE(),
            FOREIGN KEY (session_id) REFERENCES inventory_sessions(id),
            FOREIGN KEY (nomenclature_id) REFERENCES nomenclature(id)
        )
        """)
        
        conn.commit()
        print("Database schema initialized successfully")
