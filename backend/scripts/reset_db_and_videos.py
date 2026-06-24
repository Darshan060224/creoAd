import os
import shutil
from sqlalchemy import create_engine, MetaData, Table

# Setup path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT_DIR, "creoAd.db")
OUTPUT_DIR = os.path.join(ROOT_DIR, "output")

print("🧹 Starting CreoAd Database and Video Reset...")

# 1. Clean output directory
if os.path.exists(OUTPUT_DIR):
    for filename in os.listdir(OUTPUT_DIR):
        file_path = os.path.join(OUTPUT_DIR, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
            print(f"🗑 Deleted: {file_path}")
        except Exception as e:
            print(f"❌ Failed to delete {file_path}: {e}")

# 2. Clean Database tables
if os.path.exists(DB_PATH):
    engine = create_engine(f"sqlite:///{DB_PATH}")
    metadata = MetaData()
    metadata.reflect(bind=engine)
    
    with engine.begin() as connection:
        for table_name in ["campaigns", "job_logs", "team_members", "users"]:
            if table_name in metadata.tables:
                table = Table(table_name, metadata, autoload_with=engine)
                connection.execute(table.delete())
                print(f"✅ Cleared table: {table_name}")

print("✨ Cleanup and database reset complete.")
