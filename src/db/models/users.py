from sqlmodel import SQLModel, Field
from uuid import UUID, uuid4
from datetime import datetime
from typing import Optional
from ..enums import AuthProvider

class Users(SQLModel, table=True): 
    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    auth0_user_id: str = Field(unique=True, index=True) 
    provider: AuthProvider = Field()
    email_id: str = Field(unique=True)
    email_verified: bool = False
    display_name: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})