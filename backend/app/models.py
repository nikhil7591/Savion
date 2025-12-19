from sqlmodel import SQLModel, Field, Relationship
from datetime import date, datetime
from typing import Optional, List

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str = Field(unique=True, index=True)
    hashed_password: str

    sessions: List["Session"] = Relationship(back_populates="user")
    activities: List["Activity"] = Relationship(back_populates="user")

class Session(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    token: str
    device_info: Optional[str] = None
    ip_address: Optional[str] = None
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user: "User" = Relationship(back_populates="sessions")

class Activity(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    action_type: str  # e.g., login, logout, file_upload
    details: Optional[str] = None # JSON string
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user: "User" = Relationship(back_populates="activities")

class Transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str # This should eventually be a foreign key to User
    type: str  # 'income' or 'expense'
    category: str
    amount: float
    date: date
    created_at: datetime = Field(default_factory=datetime.utcnow)