import aiosqlite
import os

DB_PATH = "dj_request.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS eventos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                activo INTEGER DEFAULT 1,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS solicitudes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evento_id INTEGER NOT NULL,
                cancion TEXT NOT NULL,
                artista TEXT NOT NULL,
                spotify_id TEXT,
                portada_url TEXT,
                dedicatoria TEXT,
                votos INTEGER DEFAULT 1,
                estado TEXT DEFAULT 'pendiente',  -- pendiente | aprobada | reproducida | rechazada
                ip_solicitante TEXT,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (evento_id) REFERENCES eventos(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS votos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                solicitud_id INTEGER NOT NULL,
                ip_votante TEXT NOT NULL,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(solicitud_id, ip_votante)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS configuracion (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evento_id INTEGER NOT NULL UNIQUE,
                event_name TEXT DEFAULT 'Mi Evento',
                subtitle TEXT DEFAULT 'asong.live — DJ Request System',
                logo_url TEXT DEFAULT '',
                cashapp TEXT DEFAULT '',
                venmo TEXT DEFAULT '',
                applepay TEXT DEFAULT '',
                love_text TEXT DEFAULT 'Show Your Love',
                instagram TEXT DEFAULT '',
                tiktok TEXT DEFAULT '',
                facebook TEXT DEFAULT '',
                spotify_dj TEXT DEFAULT '',
                website TEXT DEFAULT '',
                FOREIGN KEY (evento_id) REFERENCES eventos(id)
            )
        """)
        await db.commit()

async def get_db():
    return aiosqlite.connect(DB_PATH)
