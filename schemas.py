from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UsuarioCreate(BaseModel):
    nombre: str
    correo: Optional[str] = None
    telefono: Optional[str] = None

class TarjetaCreate(BaseModel):
    codigo_tarjeta: str
    id_usuario: int

class PuntosRequest(BaseModel):
    codigo_tarjeta: str
    cantidad: int
    motivo: Optional[str] = None
    
class AdminRegister(BaseModel):
    nombre_completo: str
    correo: str
    password: str

class AdminLogin(BaseModel):
    correo: str
    password: str

class RecuperarPassword(BaseModel):
    correo: str

class UsuarioRegister(BaseModel):
    nombre: str
    correo: str
    telefono: Optional[str] = None
    password: str

class UsuarioLogin(BaseModel):
    correo: str
    password: str

class ConfirmarCodigo(BaseModel):
    correo: str
    codigo: str
    nueva_password: str

class ActividadCreate(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    lugar: Optional[str] = None
    fecha: datetime
    puntos_otorga: int = 0
    

class InscripcionCreate(BaseModel):
    id_actividad: int
    id_usuario: int
