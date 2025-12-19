from pydantic import BaseModel
from datetime import date, datetime
from typing import List

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