from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from config import DATABASE_URL

# Cấu hình engine linh hoạt: Hỗ trợ cả Cloud PostgreSQL và Local SQLite
is_sqlite = DATABASE_URL.startswith("sqlite")

if is_sqlite:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    # Tối ưu cho Supabase Supavisor Session Pooler (tránh chạm giới hạn max_client_conn & kết nối treo)
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        pool_recycle=300,
        pool_timeout=15,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Dependency injection cho FastAPI routes"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
