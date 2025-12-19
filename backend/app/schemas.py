from pydantic import BaseModel, EmailStr
from datetime import date, datetime
from typing import List, Optional

class TxIn(BaseModel):
    user_id: str
    type: str
    category: str
    amount: float
    date: date

class TxOut(TxIn):
    id: int
    created_at: datetime

class FeedbackIn(BaseModel):
    user_id: str
    feedback: str

class SummaryOut(BaseModel):
    total_income: float
    total_expense: float
    balance: float
    series: List[float]

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

class User(BaseModel):
    id: int
    name: str
    email: EmailStr

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[EmailStr] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str