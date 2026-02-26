import httpx

async def buscar_canciones(query: str, limit: int = 8) -> list:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://itunes.apple.com/search",
            params={
                "term": query,
                "media": "music",
                "limit": limit,
                "country": "US"
            }
        )
        data = response.json()

    resultados = []
    for track in data.get("results", []):
        resultados.append({
            "spotify_id": str(track["trackId"]),
            "cancion": track["trackName"],
            "artista": track["artistName"],
            "album": track.get("collectionName", ""),
            "portada_url": track["artworkUrl100"].replace("100x100", "300x300"),
            "preview_url": track.get("previewUrl"),
            "duracion_ms": track.get("trackTimeMillis", 0)
        })
    return resultados
