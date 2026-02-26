# 🎵 DJ Song Request System

Sistema completo para que los asistentes a un evento pidan canciones al DJ via QR.

## 🚀 Instalación paso a paso

### 1. Instalar dependencias
```bash
cd dj_request
pip install -r requirements.txt
```

### 2. Configurar credenciales de Spotify
```bash
# Copia el archivo de ejemplo
cp .env.example .env
```

Luego edita `.env` con tus datos:
- Ve a: https://developer.spotify.com/dashboard
- Haz click en "Create App"
- Nombre: "DJ Request" / Redirect URI: http://localhost:8000
- Copia Client ID y Client Secret al `.env`

### 3. Configurar la URL base (para QR)
En `.env`, cambia `BASE_URL` por tu IP local:
```
# Ejemplo: encuentra tu IP con `ipconfig` (Windows) o `ifconfig` (Mac/Linux)
BASE_URL=http://192.168.1.100:8000
```
Esto es importante para que el QR apunte a la dirección correcta en tu red local.

### 4. Correr el servidor
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 📱 URLs del sistema

| URL | Descripción |
|-----|-------------|
| `http://localhost:8000` | Landing móvil (lo que ven los asistentes) |
| `http://localhost:8000/dj` | Panel del DJ (tiempo real) |
| `http://localhost:8000/qr/page` | Página con el QR para imprimir/proyectar |
| `http://localhost:8000/docs` | API docs automáticos (FastAPI) |

## 🎛️ Flujo del sistema

```
Asistente escanea QR
       ↓
Busca canción en Spotify
       ↓
Agrega dedicatoria (opcional)
       ↓
Envía solicitud
       ↓
DJ ve en su panel en tiempo real ← WebSocket
       ↓
DJ aprueba / rechaza / marca como reproducida
```

## 🔐 Contraseña del DJ
Por defecto: `dj1234` — cámbiala en el `.env` con `DJ_PASSWORD=tunuevapass`

## 🛠️ Estructura del proyecto
```
dj_request/
├── main.py          # FastAPI app principal
├── database.py      # Base de datos SQLite
├── spotify.py       # Integración Spotify API
├── requirements.txt
├── .env             # Variables de entorno (¡no subir a git!)
├── .env.example     # Plantilla de variables
└── templates/
    ├── request.html # Landing móvil para asistentes
    ├── dj.html      # Panel del DJ
    └── qr.html      # Página del QR
```
