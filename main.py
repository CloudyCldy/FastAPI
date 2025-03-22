import uvicorn
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from database import engine, SessionLocal, Base
from models import User, Hamster, Device
from auth import create_token, verify_token, get_db
from utils import hash_password, verify_password
from excel_import import import_excel

# ✅ Instancia principal
app = FastAPI()

# Inicializar la base de datos
Base.metadata.create_all(bind=engine)
@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users

@app.post("/register")
def register(name: str, email: str, password: str, rol: str = "normal", db: Session = Depends(get_db)):
    hashed_password = hash_password(password)
    user = User(name=name, email=email, password=hashed_password, rol=rol)
    db.add(user)
    db.commit()
    return {"message": "User registered"}

@app.post("/login")
def login(email: str, password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token({"id": user.id, "email": user.email, "rol": user.rol})
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

#Ejecutar la API
if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=3000, reload=True)
