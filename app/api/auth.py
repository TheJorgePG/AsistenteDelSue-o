from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
import hashlib
import os
from app.core.database import get_db
from app.models.user import UserModel

router = APIRouter(prefix="/auth", tags=["Autenticación"])

def encriptar_password(password: str) -> str:
    """Función robusta de hash en Python puro para evitar errores de librerías externas en Docker."""
    salt = os.getenv("SECRET_KEY", "sueno_secure_salt")
    return hashlib.sha256((password + salt).encode('utf-8')).hexdigest()

class UserRegister(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

@router.post("/register")
def registrar_usuario(user: UserRegister, db: Session = Depends(get_db)):
    db_user = db.query(UserModel).filter(UserModel.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="El correo ya está registrado.")
    
    hashed_password = encriptar_password(user.password)
    nuevo_usuario = UserModel(email=user.email, hashed_password=hashed_password)
    
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    
    return {"status": "success", "message": "Usuario registrado correctamente", "email": nuevo_usuario.email}

@router.post("/login")
def iniciar_sesion(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(UserModel).filter(UserModel.email == user.email).first()
    password_hash = encriptar_password(user.password)
    
    if not db_user or db_user.hashed_password != password_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas")
    
    return {"status": "success", "message": "Inicio de sesión exitoso", "user_id": db_user.id}