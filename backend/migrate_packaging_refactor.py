"""
Migration: Refactor packaging module to session-based workflow
- Create new tables: packaging_sessions, packaging_session_outputs, packaging_session_waste
- Drop old table: packaging_batches (no practical use)
- Keep packaging_recipes for material calculations
"""
import pyodbc
from database import get_db_connection
from dotenv import load_dotenv

load_dotenv()

def migrate_packaging():
    """Refactor packaging to session-based workflow"""
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        print("=" * 70)
        print("PACKAGING MODULE REFACTORING")
        print("=" * 70)
        
        # Step 1: Drop old packaging_batches table
        print("\n1. Dropping old packaging_batches table...")
        try:
            cursor.execute("DROP TABLE IF EXISTS packaging_batches")
            print("   ✅ packaging_batches dropped")
        except Exception as e:
            print(f"   ⚠️  Error dropping table: {e}")
        
        # Step 2: Create packaging_sessions table
        print("\n2. Creating packaging_sessions table...")
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='packaging_sessions' AND xtype='U')
            CREATE TABLE packaging_sessions (
                id INT IDENTITY(1,1) PRIMARY KEY,
                session_number NVARCHAR(50) UNIQUE NOT NULL,
                source_product_id INT NOT NULL,
                source_weight_taken DECIMAL(10,3) NOT NULL,
                status NVARCHAR(20) NOT NULL DEFAULT 'created',
                started_at DATETIME2 NOT NULL DEFAULT DATEADD(HOUR, 2, GETDATE()),
                completed_at DATETIME2 NULL,
                operator_notes NVARCHAR(500) NULL,
                created_at DATETIME2 NOT NULL DEFAULT DATEADD(HOUR, 2, GETDATE()),
                updated_at DATETIME2 NOT NULL DEFAULT DATEADD(HOUR, 2, GETDATE()),
                FOREIGN KEY (source_product_id) REFERENCES nomenclature(id)
            )
        """)
        print("   ✅ packaging_sessions created")
        
        # Step 3: Create packaging_session_outputs table
        print("\n3. Creating packaging_session_outputs table...")
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='packaging_session_outputs' AND xtype='U')
            CREATE TABLE packaging_session_outputs (
                id INT IDENTITY(1,1) PRIMARY KEY,
                session_id INT NOT NULL,
                target_product_id INT NOT NULL,
                quantity_packed INT NOT NULL,
                calculated_materials NVARCHAR(MAX) NULL,
                confirmed_materials NVARCHAR(MAX) NULL,
                defect_quantity INT DEFAULT 0,
                notes NVARCHAR(500) NULL,
                created_at DATETIME2 NOT NULL DEFAULT DATEADD(HOUR, 2, GETDATE()),
                FOREIGN KEY (session_id) REFERENCES packaging_sessions(id) ON DELETE CASCADE,
                FOREIGN KEY (target_product_id) REFERENCES nomenclature(id)
            )
        """)
        print("   ✅ packaging_session_outputs created")
        
        # Step 4: Create packaging_session_remainders table
        print("\n4. Creating packaging_session_remainders table...")
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='packaging_session_remainders' AND xtype='U')
            CREATE TABLE packaging_session_remainders (
                id INT IDENTITY(1,1) PRIMARY KEY,
                session_id INT NOT NULL,
                nomenclature_id INT NOT NULL,
                weight_kg DECIMAL(10,3) NOT NULL,
                description NVARCHAR(200) NULL,
                notes NVARCHAR(500) NULL,
                created_at DATETIME2 NOT NULL DEFAULT DATEADD(HOUR, 2, GETDATE()),
                FOREIGN KEY (session_id) REFERENCES packaging_sessions(id) ON DELETE CASCADE,
                FOREIGN KEY (nomenclature_id) REFERENCES nomenclature(id)
            )
        """)
        print("   ✅ packaging_session_remainders created")
        
        # Step 5: Create packaging_session_waste table
        print("\n5. Creating packaging_session_waste table...")
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='packaging_session_waste' AND xtype='U')
            CREATE TABLE packaging_session_waste (
                id INT IDENTITY(1,1) PRIMARY KEY,
                session_id INT NOT NULL,
                waste_weight_kg DECIMAL(10,3) NOT NULL,
                waste_description NVARCHAR(200) NULL,
                notes NVARCHAR(500) NULL,
                created_at DATETIME2 NOT NULL DEFAULT DATEADD(HOUR, 2, GETDATE()),
                FOREIGN KEY (session_id) REFERENCES packaging_sessions(id) ON DELETE CASCADE
            )
        """)
        print("   ✅ packaging_session_waste created")
        
        # Commit all changes
        conn.commit()
        
        print("\n" + "=" * 70)
        print("MIGRATION COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print("\n📊 Summary:")
        print("  ✅ Dropped: packaging_batches")
        print("  ✅ Created: packaging_sessions")
        print("  ✅ Created: packaging_session_outputs")
        print("  ✅ Created: packaging_session_remainders")
        print("  ✅ Created: packaging_session_waste")
        print("  ✅ Kept: packaging_recipes (for calculations)")
        print("  ✅ Kept: packaging_recipe_materials")
        print()

if __name__ == "__main__":
    try:
        migrate_packaging()
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
