from database import engine
import models

def create_new_tables():
    print("Creating new tables...")
    models.Base.metadata.create_all(bind=engine)
    print("Successfully synchronized schema.")

if __name__ == "__main__":
    create_new_tables()
