from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from bson import ObjectId
from . import crud, schemas, security

router = APIRouter()


def _serialize_user(doc):
    if not doc:
        return None
    return {
        "id": str(doc.get("_id")),
        "name": doc.get("name"),
        "email": doc.get("email"),
    }


@router.post("/register")
def register(user: schemas.UserCreate):
    db_user = crud.get_user_by_email(email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    created_user = crud.create_user(user=user)
    clean_user = _serialize_user(created_user)
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": clean_user["email"], "user_id": clean_user["id"]},
        expires_delta=access_token_expires,
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": clean_user,
    }


@router.post("/login")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = crud.get_user_by_email(email=form_data.username)
    if not user or not security.verify_password(form_data.password, user.get("hashed_password")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    clean_user = _serialize_user(user)
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": clean_user["email"], "user_id": clean_user["id"]},
        expires_delta=access_token_expires,
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": clean_user,
    }
