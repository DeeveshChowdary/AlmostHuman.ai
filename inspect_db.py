import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import MetaData
import sys

# Import settings but fall back slightly
import os
import copy
from dotenv import load_dotenv
load_dotenv()

database_url = os.getenv("DATABASE_URL")
if not database_url:
    print("NO DATABASE_URL FOUND")
    sys.exit(1)

if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(database_url)

async def inspect():
    async with engine.connect() as conn:
        
        def run_inspection(sync_conn):
            from sqlalchemy import inspect as sa_inspect
            inspector = sa_inspect(sync_conn)
            tables = inspector.get_table_names()
            res = {}
            for table in tables:
                cols = inspector.get_columns(table)
                res[table] = [{"name": c["name"], "type": str(c["type"])} for c in cols]
            return res
            
        schema = await conn.run_sync(run_inspection)
        print("SCHEMA_DUMP_START")
        for table, cols in schema.items():
            print(f"TABLE: {table}")
            for col in cols:
                print(f"  - {col['name']} ({col['type']})")
        print("SCHEMA_DUMP_END")

if __name__ == "__main__":
    asyncio.run(inspect())
