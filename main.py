from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, inspect, Enum, Text
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.sql import func
import io
import time
from dotenv import load_dotenv
import os
import openpyxl

# Load environment variables
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://admin:hobito22@int.c0b28yg0kqqf.us-east-1.rds.amazonaws.com/hamstech")

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Security configuration
SECRET_KEY = os.getenv("JWT_SECRET", "hamtech")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Database Models aligned with actual schema
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50))
    email = Column(String(100), unique=True)
    password = Column(String(255))
    rol = Column(Enum('admin', 'normal', name='rol_enum'))

class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    device_name = Column(String(100))
    location = Column(String(100), nullable=True)

class Hamster(Base):
    __tablename__ = "hamsters"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String(50))
    breed = Column(String(50))
    age = Column(Integer)
    weight = Column(Integer)
    health_notes = Column(Text)
    device_id = Column(Integer)

class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"))
    temperature = Column(Float)
    humidity = Column(Float)
    recorded_at = Column(DateTime, default=func.now())

# Check and create missing tables
def check_and_create_tables():
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    needed_tables = {
        'users': User,
        'devices': Device,
        'hamsters': Hamster,
        'sensor_readings': SensorReading
    }
    
    for table_name, table_class in needed_tables.items():
        if table_name not in existing_tables:
            print(f"Creating missing table: {table_name}")
            table_class.__table__.create(bind=engine)

# Run table check on startup
check_and_create_tables()

# Pydantic Models
class UserBase(BaseModel):
    name: str
    email: str

class UserCreate(UserBase):
    password: str
    rol: str = "normal"

class UserOut(UserBase):
    id: int
    rol: str

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    dashboard: str

class TokenData(BaseModel):
    id: Optional[int] = None
    email: Optional[str] = None
    rol: Optional[str] = None

class DeviceBase(BaseModel):
    user_id: int
    device_name: str
    location: Optional[str] = None

class DeviceOut(DeviceBase):
    id: int

    class Config:
        from_attributes = True

class HamsterBase(BaseModel):
    user_id: int
    name: str
    breed: str
    age: int
    weight: int
    health_notes: Optional[str] = None
    device_id: int

class HamsterOut(HamsterBase):
    id: int

    class Config:
        from_attributes = True

class SensorDataBase(BaseModel):
    device_id: int
    temperature: float
    humidity: float

class SensorDataOut(SensorDataBase):
    id: int
    recorded_at: datetime

    class Config:
        from_attributes = True

# App setup
app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/register", response_model=UserOut)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = pwd_context.hash(user.password)
    
    db_user = User(
        name=user.name,
        email=user.email,
        password=hashed_password,
        rol=user.rol
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

@app.get("/")
async def root():
    return {"message": "Hamstech API is running"}

@app.get("/sensores", response_model=List[SensorDataOut])
async def get_sensores(db: Session = Depends(get_db)):
    sensores = db.query(SensorReading).all()
    if not sensores:
        raise HTTPException(status_code=404, detail="No sensor readings found")
    return sensores

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
