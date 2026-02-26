from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
import os, json, qrcode, io
from PIL import Image
from database import init_db, get_db
from spotify import buscar_canciones
from typing import Optional
import aiosqlite

load_dotenv()

app = FastAPI(title="DJ Song Request")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
DJ_PASSWORD = os.getenv("DJ_PASSWORD", "dj1234")

# ─── WebSocket Manager ────────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.dj_connections: list[WebSocket] = []

    async def connect_dj(self, ws: WebSocket):
        await ws.accept()
        self.dj_connections.append(ws)

    def disconnect_dj(self, ws: WebSocket):
        self.dj_connections.remove(ws)

    async def broadcast_to_dj(self, message: dict):
        for ws in self.dj_connections:
            try:
                await ws.send_json(message)
            except:
                pass

manager = ConnectionManager()

# ─── Startup ──────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    await init_db()
    # Crear evento demo si no existe
    async with aiosqlite.connect("dj_request.db") as db:
        cursor = await db.execute("SELECT COUNT(*) FROM eventos")
        count = (await cursor.fetchone())[0]
        if count == 0:
            await db.execute("INSERT INTO eventos (nombre) VALUES ('Mi Evento')")
            await db.commit()

# ─── Landing Page (móvil) ─────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    async with aiosqlite.connect("dj_request.db") as db:
        cursor = await db.execute("SELECT id, nombre FROM eventos WHERE activo=1 LIMIT 1")
        evento = await cursor.fetchone()
    return templates.TemplateResponse("request.html", {
        "request": request,
        "evento": {"id": evento[0], "nombre": evento[1]} if evento else None
    })

# ─── Buscar canciones en Spotify ──────────────────────────────────────
@app.get("/api/buscar")
async def buscar(q: str):
    if not q or len(q) < 2:
        return []
    resultados = await buscar_canciones(q)
    return resultados

# ─── Enviar solicitud ─────────────────────────────────────────────────
@app.post("/api/solicitar")
async def solicitar(request: Request, data: dict):
    evento_id = data.get("evento_id")
    cancion = data.get("cancion", "").strip()
    artista = data.get("artista", "").strip()
    spotify_id = data.get("spotify_id", "")
    portada_url = data.get("portada_url", "")
    dedicatoria = data.get("dedicatoria", "").strip()[:200]
    ip = request.client.host

    if not cancion or not artista:
        raise HTTPException(400, "Canción y artista son requeridos")

    async with aiosqlite.connect("dj_request.db") as db:
        # Evitar spam: máx 3 solicitudes por IP por evento
        cursor = await db.execute(
            "SELECT COUNT(*) FROM solicitudes WHERE evento_id=? AND ip_solicitante=? AND estado='pendiente'",
            (evento_id, ip)
        )
        count = (await cursor.fetchone())[0]
        if count >= 3:
            raise HTTPException(429, "Ya tienes 3 solicitudes pendientes. Espera a que el DJ las revise.")

        cursor = await db.execute(
            """INSERT INTO solicitudes (evento_id, cancion, artista, spotify_id, portada_url, dedicatoria, ip_solicitante)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (evento_id, cancion, artista, spotify_id, portada_url, dedicatoria, ip)
        )
        await db.commit()
        nueva_id = cursor.lastrowid

    nueva = {
        "id": nueva_id,
        "cancion": cancion,
        "artista": artista,
        "portada_url": portada_url,
        "dedicatoria": dedicatoria,
        "votos": 1,
        "estado": "pendiente"
    }
    await manager.broadcast_to_dj({"tipo": "nueva_solicitud", "solicitud": nueva})
    return {"ok": True, "id": nueva_id}

# ─── Votar por una canción ────────────────────────────────────────────
@app.post("/api/votar/{solicitud_id}")
async def votar(solicitud_id: int, request: Request):
    ip = request.client.host
    async with aiosqlite.connect("dj_request.db") as db:
        try:
            await db.execute(
                "INSERT INTO votos (solicitud_id, ip_votante) VALUES (?, ?)",
                (solicitud_id, ip)
            )
            await db.execute(
                "UPDATE solicitudes SET votos = votos + 1 WHERE id=?",
                (solicitud_id,)
            )
            await db.commit()
        except aiosqlite.IntegrityError:
            raise HTTPException(409, "Ya votaste por esta canción")

        cursor = await db.execute("SELECT votos FROM solicitudes WHERE id=?", (solicitud_id,))
        votos = (await cursor.fetchone())[0]

    await manager.broadcast_to_dj({"tipo": "voto", "solicitud_id": solicitud_id, "votos": votos})
    return {"ok": True, "votos": votos}

# ─── Ver cola pública ─────────────────────────────────────────────────
@app.get("/api/cola/{evento_id}")
async def get_cola(evento_id: int):
    async with aiosqlite.connect("dj_request.db") as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT id, cancion, artista, portada_url, dedicatoria, votos, estado, creado_en
               FROM solicitudes WHERE evento_id=? AND estado IN ('pendiente','aprobada')
               ORDER BY votos DESC, creado_en ASC""",
            (evento_id,)
        )
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]

# ─── Panel DJ ─────────────────────────────────────────────────────────
@app.get("/dj", response_class=HTMLResponse)
async def dj_panel(request: Request):
    return templates.TemplateResponse("dj.html", {"request": request})

@app.get("/api/dj/solicitudes")
async def dj_solicitudes(password: str):
    if password != DJ_PASSWORD:
        raise HTTPException(403, "Contraseña incorrecta")
    async with aiosqlite.connect("dj_request.db") as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT s.*, e.nombre as evento_nombre FROM solicitudes s
               JOIN eventos e ON e.id = s.evento_id
               WHERE s.estado IN ('pendiente','aprobada')
               ORDER BY s.votos DESC, s.creado_en ASC"""
        )
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]

@app.post("/api/dj/actualizar/{solicitud_id}")
async def dj_actualizar(solicitud_id: int, data: dict):
    if data.get("password") != DJ_PASSWORD:
        raise HTTPException(403, "Contraseña incorrecta")
    nuevo_estado = data.get("estado")
    if nuevo_estado not in ("aprobada", "reproducida", "rechazada"):
        raise HTTPException(400, "Estado inválido")

    async with aiosqlite.connect("dj_request.db") as db:
        await db.execute(
            "UPDATE solicitudes SET estado=? WHERE id=?",
            (nuevo_estado, solicitud_id)
        )
        await db.commit()

    await manager.broadcast_to_dj({
        "tipo": "estado_actualizado",
        "solicitud_id": solicitud_id,
        "estado": nuevo_estado
    })
    return {"ok": True}

# ─── WebSocket DJ ─────────────────────────────────────────────────────
@app.websocket("/ws/dj")
async def ws_dj(websocket: WebSocket):
    await manager.connect_dj(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_dj(websocket)

# ─── Generar QR ───────────────────────────────────────────────────────
@app.get("/qr")
async def generar_qr(url: Optional[str] = None):
    target = url or BASE_URL
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(target)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1DB954", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    from fastapi.responses import StreamingResponse
    return StreamingResponse(buf, media_type="image/png",
        headers={"Content-Disposition": "inline; filename=qr_dj.png"})

@app.get("/qr/page", response_class=HTMLResponse)
async def qr_page(request: Request):
    return templates.TemplateResponse("qr.html", {"request": request, "base_url": BASE_URL})
