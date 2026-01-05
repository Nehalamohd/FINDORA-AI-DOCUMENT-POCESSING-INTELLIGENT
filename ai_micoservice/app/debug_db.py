from app.database import engine
from sqlalchemy import inspect

#for development: check if tables exist
def check_tables():
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print("Tables in DB:")
        for table in tables:
            print(f"- {table}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_tables()
