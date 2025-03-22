from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware  # Import CORS middleware
from sqlalchemy.orm import Session
from database import engine, SessionLocal, Base
from models import User, Hamster, Device
from auth import create_token, verify_token, get_db
from utils import hash_password, verify_password
from excel_import import import_excel
import uvicorn



# ✅ Instancia principal
app = FastAPI()

# Configurar CORS (permitir solicitudes de tu frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://54.242.77.184:3000"],  # Permitir solicitudes desde el frontend
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

@app.post("/register")
async def register(user: UserCreate, db: Session = Depends(get_db)):
    # Verificar si el usuario ya existe
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Crear un nuevo usuario
    db_user = User(name=user.name, email=user.email, password=user.password, role=user.role)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return {"message": "Registration successful", "user_id": db_user.id}

@app.post("/login")
def login(email: str, password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token({"id": user.id, "email": user.email, "role": user.role})
    return {"token": token}

@app.get("/profile")
def get_profile(token: str, db: Session = Depends(get_db)):
    payload = verify_token(token)
    user = db.query(User).filter(User.id == payload["id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/import-excel")
async def upload_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
    return await import_excel(file, db)

@app.get("/hamsters")
def get_hamsters(db: Session = Depends(get_db)):
    hamsters = db.query(Hamster).all()
    return hamsters

@app.get("/devices")
def get_devices(db: Session = Depends(get_db)):
    devices = db.query(Device).all()
    return devices

@app.get("/")
def read_root():
    return {"message": "API running!"}

@app.get("/devices/{device_id}")
def get_device(device_id: int, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device

@app.post("/devices")
def add_device(name: str, type: str, model: str, db: Session = Depends(get_db)):
    device = Device(name=name, type=type, model=model)
    db.add(device)
    db.commit()
    db.refresh(device)
    return {"message": "Device added successfully", "deviceId": device.id}

@app.put("/devices/{device_id}")
def update_device(device_id: int, name: str, type: str, model: str, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    device.name = name
    device.type = type
    device.model = model
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

@app.get("/blog")
def get_blog():
    return {"message": "Blog page - No content yet"}

# Ejecutar la API
if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8001, reload=True)
