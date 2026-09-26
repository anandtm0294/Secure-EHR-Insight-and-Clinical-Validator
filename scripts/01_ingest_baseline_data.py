import pandas as pd  # type: ignore[import-not-found]
from sqlalchemy import text  # type: ignore[import-not-found]
from pathlib import Path

from _database import create_db_engine

def ingest_data():
    # 1. Dynamically resolve project root based on this script's location
    script_dir = Path(__file__).resolve().parent       # .../live-FDE-2/scripts
    project_root = script_dir.parent                   # .../live-FDE-2
    
    # 2. Build absolute paths to data and schema
    csv_path = project_root / 'data' / 'MIMIC_IV_Trasncript.csv'
    schema_path = project_root / 'src' / 'database' / 'schema.sql'
    
    # Verify the file actually exists before trying to read it
    if not csv_path.exists():
        raise FileNotFoundError(f"CRITICAL: Could not find dataset at {csv_path}")
        
    engine = create_db_engine()
    
    print(f"Executing schema setup from:\n  {schema_path}")
    with engine.begin() as conn:
        with open(schema_path, 'r') as file:
            conn.execute(text(file.read()))
            
    print(f"Loading clinical data from:\n  {csv_path}")
    df = pd.read_csv(csv_path)
    # Replace NaN/NaT with None so SQLAlchemy inserts SQL NULLs instead of breaking
    df = df.where(pd.notnull(df), None)
    
    print(f"Ingesting {len(df)} records into remote AWS PostgreSQL instance...")
    df.to_sql('patient_encounters', engine, if_exists='append', index=False)
    
    print("✅ Baseline legacy data ingestion complete.")

if __name__ == "__main__":
    ingest_data()
