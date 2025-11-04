from sqlmodel import SQLModel, create_engine, Session
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL= os.getenv("DATABASE_URL")

engine= create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={"connect_timeout": 5})

def init_db():
    """Initialize database tables. Call this explicitly when needed."""
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
