from database.connection import SessionLocal


def get_database():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
