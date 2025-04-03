from sqlalchemy import Column, Integer, String, ForeignKey, Text, Float, DateTime, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy import Enum
from database import Base
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.sql import func


# Definición de la tabla User
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50))
    email = Column(String(100), unique=True)
    password = Column(String(255))
    rol = Column(Enum('admin', 'normal', name='rol_enum'))
    
    devices = relationship("Device", back_populates="user")
    hamsters = relationship("Hamster", back_populates="user")

# Modelo de salida para los datos del sensor
class SensorDataOut(BaseModel):
    sensor_id: int
    temperature: float
    humidity: float
    recorded_at: datetime

    class Config:
        orm_mode = True  


class Device(Base):
    __tablename__ = 'devices'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    device_name = Column(String(100), nullable=False)
    location = Column(String(100), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)

    user = relationship("User", back_populates="devices")

    # Relación con SensorReading para obtener las lecturas de sensores asociadas al dispositivo
    sensor_readings = relationship("SensorReading", backref="device_association", lazy="dynamic")

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

class SensorData(BaseModel):
    device_id: str
    temperature: float
    humidity: float