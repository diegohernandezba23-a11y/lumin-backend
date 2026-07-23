from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP
from sqlalchemy.sql import func
from database import Base
from sqlalchemy.dialects.postgresql import UUID

class Usuario(Base):
    __tablename__ = "usuarios"
    id_usuario = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    correo = Column(String(100), unique=True)
    telefono = Column(String(20))
    id_auth = Column(UUID(as_uuid=True), nullable=True)
    fecha_registro = Column(TIMESTAMP, server_default=func.now())

class Tarjeta(Base):
    __tablename__ = "tarjetas"
    id_tarjeta = Column(Integer, primary_key=True, index=True)
    codigo_tarjeta = Column(String(20), unique=True, nullable=False)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"))
    puntos_actuales = Column(Integer, default=0)
    estado = Column(String(20), default="activa")
    fecha_registro = Column(TIMESTAMP, server_default=func.now())

class MovimientoPuntos(Base):
    __tablename__ = "movimientos_puntos"
    id_movimiento = Column(Integer, primary_key=True, index=True)
    id_tarjeta = Column(Integer, ForeignKey("tarjetas.id_tarjeta"))
    tipo = Column(String(10), nullable=False)
    cantidad = Column(Integer, nullable=False)
    motivo = Column(String(150))
    fecha = Column(TIMESTAMP, server_default=func.now())

class Administrador(Base):
    __tablename__ = "administradores"
    id_admin = Column(UUID(as_uuid=True), primary_key=True)
    nombre_completo = Column(String(150), nullable=False)
    fecha_creacion = Column(TIMESTAMP, server_default=func.now())

class Actividad(Base):
    __tablename__ = "actividades"
    id_actividad = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), nullable=False)
    descripcion = Column(String)
    lugar = Column(String(150))
    fecha = Column(TIMESTAMP, nullable=False)
    puntos_otorga = Column(Integer, default=0)
    creado_por = Column(UUID(as_uuid=True), nullable=True)
    fecha_creacion = Column(TIMESTAMP, server_default=func.now())
    

class Inscripcion(Base):
    __tablename__ = "inscripciones"
    id_inscripcion = Column(Integer, primary_key=True, index=True)
    id_actividad = Column(Integer, ForeignKey("actividades.id_actividad"))
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"))
    fecha_inscripcion = Column(TIMESTAMP, server_default=func.now())

