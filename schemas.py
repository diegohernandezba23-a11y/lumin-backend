from pydantic import BaseModel
from typing import Literal, Optional
from datetime import date, datetime, time

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
    tipo: Literal["evento", "permanente"] = "evento"
    nombre: str
    descripcion: Optional[str] = None
    lugar: Optional[str] = None
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None
    frecuencia: Optional[str] = None
    dia_semana: Optional[str] = None
    hora_inicio: Optional[time] = None
    hora_fin: Optional[time] = None
    puntos_otorga: int = 0
    estado: Literal["activa", "finalizada", "cancelada"] = "activa"

class ActividadResponse(BaseModel):
    id_actividad: int
    tipo: str
    nombre: str
    fecha: Optional[datetime] = None
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None
    lugar: Optional[str] = None
    descripcion: Optional[str] = None
    frecuencia: Optional[str] = None
    dia_semana: Optional[str] = None
    hora_inicio: Optional[time] = None
    hora_fin: Optional[time] = None
    puntos_otorga: int
    estado: str

    class Config:
        from_attributes = True

class InscripcionCreate(BaseModel):
    id_actividad: int
    id_usuario: int


class AsistenciaRegistro(BaseModel):
    usuario_id: int
    presente: bool = True
    puntos_otorgados: int = 0


class AsistenciaGuardar(BaseModel):
    fecha_asistencia: Optional[date] = None
    registros: list[AsistenciaRegistro]

class TarjetaEdit(BaseModel):
    id_usuario: Optional[int] = None
    estado: Optional[str] = None