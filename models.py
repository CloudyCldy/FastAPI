from sqlalchemy import Column, Integer, String, ForeignKey, Text, Float, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy import Enum
from database import Base
from pydantic import BaseModel
from datetime import datetime

# Definición de la tabla User
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50))
    email = Column(String(100), unique=True)
    password = Column(String(255))
    rol = Column(Enum('admin', 'normal', name='rol_enum'))

    # Relación con Hamster (opcional si la tienes)
    hamsters = relationship("Hamster", back_populates="user")

# Modelo de salida para los datos del sensor
class SensorDataOut(BaseModel):
    sensor_id: int
    temperature: float
    humidity: float
    recorded_at: datetime

    class Config:
        orm_mode = True  # Permite la conversión automática de ORM a Pydantic

class Device(Base):
    __tablename__ = 'devices'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    # otras columnas

class Hamster(Base):
    __tablename__ = 'hamsters'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    user_id = Column(Integer, ForeignKey('users.id'))  # Relación con User
    device_id = Column(Integer, ForeignKey('devices.id'))  # Relación con Device

    # Relación con Device
    device = relationship("Device", backref="hamsters")
    
    # Relación con User
    user = relationship("User", back_populates="hamsters")

    # otras columnas, como por ejemplo un campo de edad o estado
    age = Column(Integer)

class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"))
    temperature = Column(Float)
    humidity = Column(Float)
    recorded_at = Column(DateTime, default=datetime.utcnow)

    # Relación con Device
    device = relationship("Device", backref="sensor_readings")

# Modelos de entrada (Pydantic models)
class SensorReadingCreate(BaseModel):
    device_id: int
    temperature: float
    humidity: float
    recorded_at: datetime

    class Config:
        orm_mode = True

class HamsterCreate(BaseModel):
    name: str
    user_id: int
    device_id: int
    age: int

    class Config:
        orm_mode = True
