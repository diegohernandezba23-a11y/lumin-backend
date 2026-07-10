from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import engine, get_db, Base
import models
import schemas
from auth_client import supabase

Base.metadata.create_all(bind=engine)

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


@app.get("/")
def home():
    return {"mensaje": "Lumin API funcionando"}

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