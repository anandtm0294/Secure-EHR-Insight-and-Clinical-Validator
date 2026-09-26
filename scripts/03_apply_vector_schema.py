import os
from sqlalchemy import URL, create_engine, text
from dotenv import load_dotenv

def apply_pgvector():
    load_dotenv(override=True)
    
    required_vars = ("DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT", "DB_NAME")
    missing_vars = [name for name in required_vars if not os.getenv(name)]
    if missing_vars:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )

    db_url = URL.create(
        drivername="postgresql+psycopg",
        username=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        database=os.environ["DB_NAME"],
    )
    engine = create_engine(db_url)
    
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
