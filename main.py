from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Header
from fastapi.middleware.cors import CORSMiddleware  # Import CORS middleware
from sqlalchemy.orm import Session
from database import engine, SessionLocal, Base
from models import User, Hamster, Device, SensorDataOut, SensorReading,SensorData  # Asegúrate de tener 'SensorReading' en models
from auth import create_token, verify_token, get_db
from utils import hash_password, verify_password
from excel_import import import_excel
import uvicorn
from pydantic import BaseModel
from typing import List  # Importar List para usarlo como tipo de datos en la respuesta
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine



# ✅ Instancia principal
app = FastAPI()

# Configurar CORS (permitir solicitudes de tu frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://34.228.9.133:3000"],  # Permitir solicitudes desde el frontend
    allow_credentials=True,
    allow_methods=["*"],  # Permitir todos los métodos HTTP (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Permitir todos los encabezados
)

# Inicializar la base de datos
Base.metadata.create_all(bind=engine)

@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users

class UserRegister(BaseModel):
    name: str
    email: str
    password: str
    rol: str = "normal"

@app.post("/register")
def register(user: UserRegister, db: Session = Depends(get_db)):
    if user.rol not in ['admin', 'normal']:
        raise HTTPException(status_code=400, detail="Invalid rol. Must be 'admin' or 'normal'.")
    
    hashed_password = hash_password(user.password)
    new_user = User(name=user.name, email=user.email, password=hashed_password, rol=user.rol)
    db.add(new_user)
    db.commit()

    return {"message": "User registered"}

class UserLogin(BaseModel):
    email: str
    password: str

@app.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    
    if not db_user or not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token({"id": db_user.id, "email": db_user.email, "rol": db_user.rol})
    return {"token": token}

@app.get("/profile")
def get_profile(
    authorization: str = Header(None),  # Extraer el encabezado Authorization
    db: Session = Depends(get_db)
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token no proporcionado o inválido")
    
    token = authorization.split("Bearer ")[1]
    
    try:
        payload = verify_token(token)
        user = db.query(User).filter(User.id == payload["id"]).first()
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        return user
    except Exception as e:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

@app.post("/import-excel")
async def upload_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
    return await import_excel(file, db)

@app.get("/hamsters")
def get_hamsters(db: Session = Depends(get_db)):
    hamsters = db.query(Hamster).all()
    return hamsters

@app.get("/devices")
def get_devices(db: Session = Depends(get_db)):
    return db.query(Device).all()

@app.get("/devices/{device_id}")
def get_device(device_id: int, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device

@app.post("/devices")
def add_device(device_name: str, location: str = None, user_id: int = None, db: Session = Depends(get_db)):
    device = Device(device_name=device_name, location=location, user_id=user_id)
    db.add(device)
    db.commit()
    db.refresh(device)
    return {"message": "Device added successfully", "deviceId": device.id}

@app.put("/devices/{device_id}")
def update_device(device_id: int, device_name: str = None, location: str = None, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if device_name:
        device.device_name = device_name
    if location is not None:
        device.location = location
    
    db.commit()
    db.refresh(device)
    return {"message": "Device updated successfully"}

@app.delete("/devices/{device_id}")
def delete_device(device_id: int, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    db.delete(device)
    db.commit()
    return {"message": "Device deleted successfully"}
@app.get("/")
def read_root():
    return {"message": "API running!"}

@app.get("/blog")
def get_blog():
    return {"message": "Blog page - No content yet"}

@app.get("/sensores", response_model=List[SensorDataOut])
def get_sensores(db: Session = Depends(get_db)):
    sensores = db.query(SensorReading).all()
    
    if not sensores:
        raise HTTPException(status_code=404, detail="No sensor readings found")
    
    return [
        SensorDataOut(
            sensor_id=sensor.device_id,  # Asegúrate de que 'device_id' esté disponible en tu consulta
            temperature=sensor.temperature,
            humidity=sensor.humidity,
            recorded_at=sensor.recorded_at
        ) 
        for sensor in sensores
    ]


# Endpoint para guardar los datos del sensor
@app.post("/sensor-data")
async def save_sensor_data(sensor_data: SensorData, db: AsyncSession = Depends(get_db)):
    if not sensor_data.device_id or sensor_data.temperature is None or sensor_data.humidity is None:
        raise HTTPException(status_code=400, detail="Missing fields")

    try:
        # Guardando los datos en la base de datos
        new_data = SensorReading(
            device_id=sensor_data.device_id,
            temperature=sensor_data.temperature,
            humidity=sensor_data.humidity
        )
        db.add(new_data)
        await db.commit()

        # Log de los datos guardados
        print(f"Datos guardados: Device: {sensor_data.device_id}, Temp: {sensor_data.temperature}C, Hum: {sensor_data.humidity}%")
        return {"message": "Data saved successfully", "id": new_data.id}

    except SQLAlchemyError as error:
        print("Error saving data:", error)
        raise HTTPException(status_code=500, detail="Server error")

# Ejecutar la API
if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8001, reload=True)
