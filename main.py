from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, inspect, Enum,Text
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

# Security functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("email")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.email == token_data.email).first()
    if user is None:
        raise credentials_exception
    
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "rol": user.rol
    }

# Login attempts tracking
login_attempts = {}

# Routes
@app.post("/register", response_model=UserOut)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    
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

@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    email = form_data.username
    password = form_data.password
    
    if email in login_attempts and login_attempts[email]["attempts"] >= 3:
        time_diff = (datetime.now() - login_attempts[email]["time"]).total_seconds()
        if time_diff < 300:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Too many attempts. Try again in 5 minutes."
            )
        else:
            del login_attempts[email]
    
    user = db.query(User).filter(User.email == email).first()
    
    if not user or not verify_password(password, user.password):
        if email not in login_attempts:
            login_attempts[email] = {"attempts": 1, "time": datetime.now()}
        else:
            login_attempts[email]["attempts"] += 1
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if email in login_attempts:
        del login_attempts[email]
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "id": user.id, 
            "email": user.email, 
            "rol": user.rol
        },
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "dashboard": f"/dashboard/{user.rol}"
    }

@app.get("/users", response_model=List[UserOut])
async def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users

@app.get("/devices", response_model=List[DeviceOut])
async def get_devices(db: Session = Depends(get_db)):
    devices = db.query(Device).all()
    return [{
        "id": d.id,
        "user_id": d.user_id,
        "device_name": d.device_name,
        "location": d.location
    } for d in devices]

@app.post("/devices", response_model=DeviceOut)
async def create_device(device: DeviceBase, db: Session = Depends(get_db)):
    db_device = Device(
        user_id=device.user_id,
        device_name=device.device_name,
        location=device.location
    )
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device

@app.get("/hamsters", response_model=List[HamsterOut])
async def get_hamsters(db: Session = Depends(get_db)):
    hamsters = db.query(Hamster).all()
    return hamsters

@app.post("/hamsters", response_model=HamsterOut)
async def create_hamster(hamster: HamsterBase, db: Session = Depends(get_db)):
    db_hamster = Hamster(
        user_id=hamster.user_id,
        name=hamster.name,
        breed=hamster.breed,
        age=hamster.age,
        weight=hamster.weight,
        health_notes=hamster.health_notes,
        device_id=hamster.device_id
    )
    db.add(db_hamster)
    db.commit()
    db.refresh(db_hamster)
    return db_hamster

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