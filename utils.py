from argon2 import PasswordHasher

# Instancia del hasher
ph = PasswordHasher()

# Función para hashear contraseñas
def hash_password(password: str) -> str:
    return ph.hash(password)

# Función para verificar contraseñas
def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        # Verificar la contraseña
        ph.verify(hashed_password, plain_password)
        return True
    except Exception:
        # Si la contraseña no es válida
        return False
