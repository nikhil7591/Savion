from pydantic import BaseModel, Field, GetJsonSchemaHandler, ConfigDict, field_validator
from pydantic.json_schema import JsonSchemaValue
from datetime import date, datetime
from typing import Optional, Any, Annotated
from bson import ObjectId

class PyObjectId(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return str(v)
        if isinstance(v, str):
            if ObjectId.is_valid(v):
                return v
            raise ValueError("Invalid ObjectId format")
        raise ValueError("Invalid ObjectId")

    @classmethod
    def __get_pydantic_json_schema__(cls, schema: dict[str, Any], handler: GetJsonSchemaHandler) -> JsonSchemaValue:
        return {"type": "string", "description": "MongoDB ObjectId as string"}

class Transaction(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            ObjectId: str,
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
        }
    )
    
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    user_id: str
    type: str  # 'income' or 'expense'
    category: str
    amount: float
    date: date
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

class User(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            ObjectId: str,
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
        }
    )
    
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    email: str
    name: Optional[str] = None
    password_hash: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
