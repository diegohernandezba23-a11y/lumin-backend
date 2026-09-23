from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import inspect, text
from datetime import date, datetime
from database import engine, get_db, Base
import models
import schemas
from auth_client import supabase

Base.metadata.create_all(bind=engine)


def migrate_actividades_schema():
    """Bring existing deployments up to date with the activity model."""
    inspector = inspect(engine)
    if "actividades" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("actividades")}
    column_definitions = {
        "tipo": "VARCHAR(20) NOT NULL DEFAULT 'evento'",
        "fecha_inicio": "TIMESTAMP NULL",
        "fecha_fin": "TIMESTAMP NULL",
        "frecuencia": "VARCHAR(20) NULL",
        "dia_semana": "VARCHAR(20) NULL",
        "hora_inicio": "TIME NULL",
        "hora_fin": "TIME NULL",
    }

    with engine.begin() as connection:
        for column_name, definition in column_definitions.items():
            if column_name not in columns:
                connection.execute(text(
                    f"ALTER TABLE actividades ADD COLUMN {column_name} {definition}"
                ))

        if engine.dialect.name == "postgresql":
            connection.execute(text(
                "ALTER TABLE actividades "
                "ALTER COLUMN fecha_inicio DROP NOT NULL, "
                "ALTER COLUMN fecha_fin DROP NOT NULL"
            ))


migrate_actividades_schema()

app = FastAPI(title="Lumin API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"mensaje": "Lumin API funcionando"}

# ---------- PING (mantener viva la base de datos / evitar pausa de Supabase) ----------
@app.get("/ping")
def ping(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}

# ---------- REGISTRAR USUARIO ----------
@app.post("/usuarios")
def crear_usuario(usuario: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    nuevo = models.Usuario(**usuario.dict())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

# ---------- REGISTRAR TARJETA ----------
@app.post("/tarjetas")
def crear_tarjeta(tarjeta: schemas.TarjetaCreate, db: Session = Depends(get_db)):
    existe = db.query(models.Tarjeta).filter(
        models.Tarjeta.codigo_tarjeta == tarjeta.codigo_tarjeta
    ).first()
    if existe:
        raise HTTPException(status_code=400, detail="Esa tarjeta ya existe")
    nueva = models.Tarjeta(**tarjeta.dict())
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva

# ---------- VER PUNTOS DE UNA TARJETA ----------
@app.get("/tarjetas/{codigo_tarjeta}")
def ver_tarjeta(codigo_tarjeta: str, db: Session = Depends(get_db)):
    tarjeta = db.query(models.Tarjeta).filter(
        models.Tarjeta.codigo_tarjeta == codigo_tarjeta
    ).first()
    if not tarjeta:
        raise HTTPException(status_code=404, detail="Tarjeta no encontrada")
    return tarjeta

# ---------- AÑADIR PUNTOS ----------
@app.post("/puntos/sumar")
def sumar_puntos(datos: schemas.PuntosRequest, db: Session = Depends(get_db)):
    tarjeta = db.query(models.Tarjeta).filter(
        models.Tarjeta.codigo_tarjeta == datos.codigo_tarjeta
    ).first()
    if not tarjeta:
        raise HTTPException(status_code=404, detail="Tarjeta no encontrada")

    tarjeta.puntos_actuales += datos.cantidad

    movimiento = models.MovimientoPuntos(
        id_tarjeta=tarjeta.id_tarjeta,
        tipo="suma",
        cantidad=datos.cantidad,
        motivo=datos.motivo,
    )
    db.add(movimiento)
    db.commit()
    db.refresh(tarjeta)
    return {"mensaje": "Puntos añadidos", "puntos_actuales": tarjeta.puntos_actuales}

# ---------- QUITAR PUNTOS ----------
@app.post("/puntos/quitar")
def quitar_puntos(datos: schemas.PuntosRequest, db: Session = Depends(get_db)):
    tarjeta = db.query(models.Tarjeta).filter(
        models.Tarjeta.codigo_tarjeta == datos.codigo_tarjeta
    ).first()
    if not tarjeta:
        raise HTTPException(status_code=404, detail="Tarjeta no encontrada")
    if tarjeta.puntos_actuales < datos.cantidad:
        raise HTTPException(status_code=400, detail="No hay suficientes puntos")

    tarjeta.puntos_actuales -= datos.cantidad

    movimiento = models.MovimientoPuntos(
        id_tarjeta=tarjeta.id_tarjeta,
        tipo="resta",
        cantidad=datos.cantidad,
        motivo=datos.motivo,
    )
    db.add(movimiento)
    db.commit()
    db.refresh(tarjeta)
    return {"mensaje": "Puntos descontados", "puntos_actuales": tarjeta.puntos_actuales}

# ---------- REGISTRAR ADMINISTRADOR ----------
@app.post("/admin/registrar")
def registrar_admin(datos: schemas.AdminRegister, db: Session = Depends(get_db)):
    respuesta = supabase.auth.sign_up({
        "email": datos.correo,
        "password": datos.password
    })

    if respuesta.user is None:
        raise HTTPException(status_code=400, detail="No se pudo crear la cuenta")

    nuevo_admin = models.Administrador(
        id_admin=respuesta.user.id,
        nombre_completo=datos.nombre_completo
    )
    db.add(nuevo_admin)
    db.commit()

    return {"mensaje": "Administrador registrado correctamente"}

# ---------- LOGIN ----------
@app.post("/admin/login")
def login_admin(datos: schemas.AdminLogin):
    try:
        respuesta = supabase.auth.sign_in_with_password({
            "email": datos.correo,
            "password": datos.password
        })
    except Exception:
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")

    return {
        "mensaje": "Login exitoso",
        "access_token": respuesta.session.access_token
    }

# ---------- RECUPERAR CONTRASEÑA ----------
@app.post("/admin/recuperar-password")
def recuperar_password(datos: schemas.RecuperarPassword):
    supabase.auth.reset_password_for_email(datos.correo)
    return {"mensaje": "Si el correo existe, se envió un link de recuperación"}

# ---------- REGISTRAR USUARIO (con login) ----------
@app.post("/usuarios/registrar")
def registrar_usuario(datos: schemas.UsuarioRegister, db: Session = Depends(get_db)):
    respuesta = supabase.auth.sign_up({
        "email": datos.correo,
        "password": datos.password
    })

    if respuesta.user is None:
        raise HTTPException(status_code=400, detail="No se pudo crear la cuenta")

    nuevo_usuario = models.Usuario(
        nombre=datos.nombre,
        correo=datos.correo,
        telefono=datos.telefono,
        id_auth=respuesta.user.id
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)

    return {"mensaje": "Cuenta creada correctamente", "id_usuario": nuevo_usuario.id_usuario}

# ---------- CONFIRMAR CÓDIGO Y CAMBIAR CONTRASEÑA ----------
@app.post("/admin/confirmar-codigo")
def confirmar_codigo(datos: schemas.ConfirmarCodigo):
    try:
        supabase.auth.verify_otp({
            "email": datos.correo,
            "token": datos.codigo,
            "type": "recovery"
        })
    except Exception:
        raise HTTPException(status_code=400, detail="Código incorrecto o expirado")

    supabase.auth.update_user({
        "password": datos.nueva_password
    })

    return {"mensaje": "Contraseña actualizada correctamente"}


# ---------- LOGIN USUARIO ----------
@app.post("/usuarios/login")
def login_usuario(datos: schemas.UsuarioLogin, db: Session = Depends(get_db)):
    try:
        respuesta = supabase.auth.sign_in_with_password({
            "email": datos.correo,
            "password": datos.password
        })
    except Exception:
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")

    usuario = db.query(models.Usuario).filter(
        models.Usuario.id_auth == respuesta.user.id
    ).first()

    return {
        "mensaje": "Login exitoso",
        "access_token": respuesta.session.access_token,
        "id_usuario": usuario.id_usuario,
        "nombre": usuario.nombre
    }

# ---------- CREAR ACTIVIDAD (admin) ----------
@app.post("/actividades")
def crear_actividad(datos: schemas.ActividadCreate, db: Session = Depends(get_db)):
    nueva = models.Actividad(
        tipo=datos.tipo,
        nombre=datos.nombre,
        descripcion=datos.descripcion,
        lugar=datos.lugar,
        fecha=datos.fecha_inicio or datos.fecha_fin or datetime.utcnow(),
        fecha_inicio=datos.fecha_inicio,
        fecha_fin=datos.fecha_fin,
        frecuencia=datos.frecuencia,
        dia_semana=datos.dia_semana,
        hora_inicio=datos.hora_inicio,
        hora_fin=datos.hora_fin,
        puntos_otorga=datos.puntos_otorga,
        estado=datos.estado,
    )
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva

# ---------- LISTAR ACTIVIDADES (admin y usuario) ----------
@app.get("/actividades", response_model=list[schemas.ActividadResponse])
def listar_actividades(db: Session = Depends(get_db)):
    return db.query(models.Actividad).order_by(models.Actividad.fecha_inicio).all()

# ---------- INSCRIBIRSE A UNA ACTIVIDAD (usuario) ----------
@app.post("/inscripciones")
def inscribirse(datos: schemas.InscripcionCreate, db: Session = Depends(get_db)):
    ya_existe = db.query(models.Inscripcion).filter(
        models.Inscripcion.id_actividad == datos.id_actividad,
        models.Inscripcion.id_usuario == datos.id_usuario,
    ).first()
    if ya_existe:
        raise HTTPException(status_code=400, detail="Ya estás inscrito en esta actividad")

    nueva = models.Inscripcion(id_actividad=datos.id_actividad, id_usuario=datos.id_usuario)
    db.add(nueva)
    db.commit()
    return {"mensaje": "Inscripción exitosa"}

# ---------- HISTORIAL DE UNA TARJETA (con datos del dueño) ----------
@app.get("/tarjetas/{codigo_tarjeta}/completo")
def tarjeta_completa(codigo_tarjeta: str, db: Session = Depends(get_db)):
    tarjeta = db.query(models.Tarjeta).filter(
        models.Tarjeta.codigo_tarjeta == codigo_tarjeta
    ).first()
    if not tarjeta:
        raise HTTPException(status_code=404, detail="Tarjeta no encontrada")

    usuario = db.query(models.Usuario).filter(
        models.Usuario.id_usuario == tarjeta.id_usuario
    ).first()

    movimientos = db.query(models.MovimientoPuntos).filter(
        models.MovimientoPuntos.id_tarjeta == tarjeta.id_tarjeta
    ).order_by(models.MovimientoPuntos.fecha.desc()).all()

    return {
        "tarjeta": {
            "codigo_tarjeta": tarjeta.codigo_tarjeta,
            "puntos_actuales": tarjeta.puntos_actuales,
            "estado": tarjeta.estado,
        },
        "usuario": {
            "nombre": usuario.nombre if usuario else None,
            "correo": usuario.correo if usuario else None,
            "telefono": usuario.telefono if usuario else None,
        },
        "movimientos": [
            {
                "tipo": m.tipo,
                "cantidad": m.cantidad,
                "motivo": m.motivo,
                "fecha": m.fecha.isoformat(),
            } for m in movimientos
        ],
    }

@app.get("/usuarios/{id_usuario}/tarjeta")
def tarjeta_de_usuario(id_usuario: int, db: Session = Depends(get_db)):
    tarjeta = db.query(models.Tarjeta).filter(
        models.Tarjeta.id_usuario == id_usuario
    ).first()
    if not tarjeta:
        raise HTTPException(status_code=404, detail="No tienes tarjeta registrada todavía")

    movimientos = db.query(models.MovimientoPuntos).filter(
        models.MovimientoPuntos.id_tarjeta == tarjeta.id_tarjeta
    ).order_by(models.MovimientoPuntos.fecha.desc()).all()

    usuario = db.query(models.Usuario).filter(models.Usuario.id_usuario == id_usuario).first()

    return {
        "tarjeta": {
            "codigo_tarjeta": tarjeta.codigo_tarjeta,
            "puntos_actuales": tarjeta.puntos_actuales,
            "estado": tarjeta.estado,
        },
        "usuario": {
            "id_usuario": usuario.id_usuario if usuario else None,
            "nombre": usuario.nombre if usuario else None,
            "correo": usuario.correo if usuario else None,
            "telefono": usuario.telefono if usuario else None,
        },
        "movimientos": [
            {"tipo": m.tipo, "cantidad": m.cantidad, "motivo": m.motivo, "fecha": m.fecha.isoformat()}
            for m in movimientos
        ],
    }

# ---------- EDITAR / ELIMINAR ACTIVIDAD ----------
@app.put("/actividades/{id_actividad}")
def editar_actividad(id_actividad: int, datos: schemas.ActividadCreate, db: Session = Depends(get_db)):
    actividad = db.query(models.Actividad).filter(models.Actividad.id_actividad == id_actividad).first()
    if not actividad:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")
    actividad.tipo = datos.tipo
    actividad.nombre = datos.nombre
    actividad.descripcion = datos.descripcion
    actividad.lugar = datos.lugar
    actividad.fecha = datos.fecha_inicio or datos.fecha_fin or datetime.utcnow()
    actividad.fecha_inicio = datos.fecha_inicio
    actividad.fecha_fin = datos.fecha_fin
    actividad.frecuencia = datos.frecuencia
    actividad.dia_semana = datos.dia_semana
    actividad.hora_inicio = datos.hora_inicio
    actividad.hora_fin = datos.hora_fin
    actividad.puntos_otorga = datos.puntos_otorga
    actividad.estado = datos.estado
    db.commit()
    db.refresh(actividad)
    return actividad

@app.delete("/actividades/{id_actividad}")
def eliminar_actividad(id_actividad: int, db: Session = Depends(get_db)):
    actividad = db.query(models.Actividad).filter(models.Actividad.id_actividad == id_actividad).first()
    if not actividad:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")
    db.query(models.Inscripcion).filter(models.Inscripcion.id_actividad == id_actividad).delete()
    db.delete(actividad)
    db.commit()
    return {"mensaje": "Actividad eliminada"}

# ---------- VER INSCRITOS DE UNA ACTIVIDAD ----------
@app.get("/actividades/{id_actividad}/inscritos")
def ver_inscritos(id_actividad: int, db: Session = Depends(get_db)):
    inscripciones = db.query(models.Inscripcion).filter(models.Inscripcion.id_actividad == id_actividad).all()
    resultado = []
    for insc in inscripciones:
        usuario = db.query(models.Usuario).filter(models.Usuario.id_usuario == insc.id_usuario).first()
        resultado.append({
            "id_usuario": insc.id_usuario,
            "nombre": usuario.nombre if usuario else "Desconocido",
            "correo": usuario.correo if usuario else None,
        })
    return resultado


# ---------- TOMAR ASISTENCIA ----------
@app.get("/actividades/{id_actividad}/asistencia")
def ver_asistencia(id_actividad: int, fecha_asistencia: date | None = None, db: Session = Depends(get_db)):
    actividad = db.query(models.Actividad).filter(
        models.Actividad.id_actividad == id_actividad
    ).first()
    if not actividad:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")

    fecha = fecha_asistencia or date.today()
    inscripciones = db.query(models.Inscripcion).filter(
        models.Inscripcion.id_actividad == id_actividad
    ).all()
    registros = db.query(models.Asistencia).filter(
        models.Asistencia.actividad_id == id_actividad,
        models.Asistencia.fecha_asistencia == fecha,
    ).all()
    por_usuario = {registro.usuario_id: registro for registro in registros}

    resultado = []
    for inscripcion in inscripciones:
        usuario = db.query(models.Usuario).filter(
            models.Usuario.id_usuario == inscripcion.id_usuario
        ).first()
        registro = por_usuario.get(inscripcion.id_usuario)
        resultado.append({
            "usuario_id": inscripcion.id_usuario,
            "nombre": usuario.nombre if usuario else "Desconocido",
            "presente": registro.presente if registro else False,
            "puntos_otorgados": registro.puntos_otorgados if registro else 0,
        })
    return {"actividad_id": id_actividad, "fecha_asistencia": fecha, "registros": resultado}


@app.put("/actividades/{id_actividad}/asistencia")
def guardar_asistencia(
    id_actividad: int,
    datos: schemas.AsistenciaGuardar,
    db: Session = Depends(get_db),
):
    actividad = db.query(models.Actividad).filter(
        models.Actividad.id_actividad == id_actividad
    ).first()
    if not actividad:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")

    fecha = datos.fecha_asistencia or date.today()
    usuarios_inscritos = {
        inscripcion.id_usuario for inscripcion in db.query(models.Inscripcion).filter(
            models.Inscripcion.id_actividad == id_actividad
        ).all()
    }
    usuarios_enviados = {registro.usuario_id for registro in datos.registros}
    no_inscritos = usuarios_enviados - usuarios_inscritos
    if no_inscritos:
        raise HTTPException(
            status_code=400,
            detail=f"Usuarios no inscritos: {sorted(no_inscritos)}",
        )

    for registro in datos.registros:
        asistencia = db.query(models.Asistencia).filter(
            models.Asistencia.actividad_id == id_actividad,
            models.Asistencia.usuario_id == registro.usuario_id,
            models.Asistencia.fecha_asistencia == fecha,
        ).first()
        if asistencia:
            asistencia.presente = registro.presente
            asistencia.puntos_otorgados = registro.puntos_otorgados
        else:
            db.add(models.Asistencia(
                actividad_id=id_actividad,
                usuario_id=registro.usuario_id,
                fecha_asistencia=fecha,
                presente=registro.presente,
                puntos_otorgados=registro.puntos_otorgados,
            ))

    db.commit()
    return {"mensaje": "Asistencia guardada", "fecha_asistencia": fecha}

# ---------- EDITAR / ELIMINAR TARJETA ----------
@app.put("/tarjetas/{codigo_tarjeta}")
def editar_tarjeta(codigo_tarjeta: str, datos: schemas.TarjetaEdit, db: Session = Depends(get_db)):
    tarjeta = db.query(models.Tarjeta).filter(models.Tarjeta.codigo_tarjeta == codigo_tarjeta).first()
    if not tarjeta:
        raise HTTPException(status_code=404, detail="Tarjeta no encontrada")
    if datos.id_usuario is not None:
        tarjeta.id_usuario = datos.id_usuario
    if datos.estado is not None:
        tarjeta.estado = datos.estado
    db.commit()
    db.refresh(tarjeta)
    return tarjeta

@app.delete("/tarjetas/{codigo_tarjeta}")
def eliminar_tarjeta(codigo_tarjeta: str, db: Session = Depends(get_db)):
    tarjeta = db.query(models.Tarjeta).filter(models.Tarjeta.codigo_tarjeta == codigo_tarjeta).first()
    if not tarjeta:
        raise HTTPException(status_code=404, detail="Tarjeta no encontrada")
    db.query(models.MovimientoPuntos).filter(models.MovimientoPuntos.id_tarjeta == tarjeta.id_tarjeta).delete()
    db.delete(tarjeta)
    db.commit()
    return {"mensaje": "Tarjeta eliminada"}