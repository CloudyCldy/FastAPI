from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50))
    email = Column(String(100), unique=True)
    password = Column(String(255))
    rol = Column(String(20))

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

class Device(Base):
    __tablename__ = "devices"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    device_name = Column(String)  
    location = Column(String)
