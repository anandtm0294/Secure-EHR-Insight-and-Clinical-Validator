from sqlalchemy import text

from _database import create_db_engine

def apply_pgvector():
    engine = create_db_engine()
    
    print("🚀 Connecting to AWS to apply pgvector schema upgrade...")
    
    try:
        with engine.begin() as conn:
            # Note: Extension was activated via DBA superuser. 
            # We only alter the application table here.
            print("Adding 'clinical_embedding' column (768 dimensions)...")
            conn.execute(text("ALTER TABLE patient_encounters ADD COLUMN IF NOT EXISTS clinical_embedding vector(768);"))
            
            # Verify the column was added
            verify = conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'patient_encounters' AND column_name = 'clinical_embedding';
            """)).fetchone()
            
            if verify:
                print(f"✅ Schema upgrade complete. Confirmed column: {verify[0]} ({verify[1]})")
            else:
                print("❌ Column not found after alter attempt.")
            
    except Exception as e:
        print(f"❌ Error applying schema: {e}")

if __name__ == "__main__":
    apply_pgvector()
