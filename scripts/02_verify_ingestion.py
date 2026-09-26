import os
import pandas as pd
from sqlalchemy import URL, create_engine, text
from dotenv import load_dotenv

def verify_ingestion():
    # Load environment variables
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
    
    print("🔍 Verifying Data Integrity in AWS PostgreSQL...\n")
    
    with engine.connect() as conn:
        # 1. Check Total Row Count
        count_result = conn.execute(text("SELECT COUNT(*) FROM patient_encounters")).scalar()
        print(f"Total records found: {count_result}")
        
        if count_result == 0:
            print("⚠️ Warning: Table is empty. Ingestion may have failed.")
            return
            
        # 2. Retrieve a Sample of Critical Clinical Columns
        # We select specific columns so the terminal output is readable
        print("\nFetching sample clinical records...")
        query = text("""
            SELECT 
                subject_id, 
                admission_type, 
                drug, 
                drg_severity 
            FROM patient_encounters 
            WHERE drug IS NOT NULL
            LIMIT 5
        """)
        
        # Use Pandas for clean terminal formatting
        sample_df = pd.read_sql(query, conn)
        
        print("-" * 65)
        print(sample_df.to_string(index=False))
        print("-" * 65)
        print("\n✅ Verification complete. Legacy database state is confirmed.")

if __name__ == "__main__":
    verify_ingestion()
