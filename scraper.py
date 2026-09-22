import json
import os
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

# Configuración
HANDLE = "@Dobshman"
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
KEYWORDS = [
    "drop",
    "forced",
    "forzado",
    "actualizacion",
    "actualización",
    "update",
]
DB_FILE = "sent_videos.txt"
TIMEOUT = 10  # Tiempo límite en segundos para las peticiones HTTP


def get_channel_id(handle):
    """Obtiene el Channel ID ('UC...') mediante scraping ligero de la página del canal."""
    # Asegurar el formato con @
    if not handle.startswith("@"):
        handle = f"@{handle}"

    url = f"https://www.youtube.com/{handle}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Cookie": "SOCS=CAI",  # Salta la pantalla de consentimiento de cookies
    }

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            html = resp.read().decode("utf-8")

        # Patrones de búsqueda por orden de fiabilidad
        patterns = [
            r'itemprop="channelId"\s+content="(UC[a-zA-Z0-9_-]{22})"',
            r'"externalId":"(UC[a-zA-Z0-9_-]{22})"',
            r'"channelId":"(UC[a-zA-Z0-9_-]{22})"',
            r"channel_id=(UC[a-zA-Z0-9_-]{22})",
            r'youtube\.com/channel/(UC[a-zA-Z0-9_-]{22})"',
        ]

        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                return match.group(1)

    except urllib.error.URLError as e:
        print(f"Error de red al resolver el ID del canal para {handle}: {e}")
    except Exception as e:
        print(f"Error inesperado al resolver el ID para {handle}: {e}")

    return None


def load_sent_videos():
    """Carga el conjunto de IDs de vídeos ya enviados."""
    if not os.path.exists(DB_FILE):
        return set()
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    except IOError as e:
        print(f"Error al leer {DB_FILE}: {e}")
        return set()


def save_sent_video(video_id):
    """Guarda un ID de vídeo en el archivo local."""
    try:
        with open(DB_FILE, "a", encoding="utf-8") as f:
            f.write(f"{video_id}\n")
    except IOError as e:
        print(f"Error al guardar el ID {video_id} en {DB_FILE}: {e}")


def matches_keywords(text, keywords):
    """Comprueba si alguna palabra clave está presente en el texto usando límites de palabra."""
    text_lower = text.lower()
    for kw in keywords:
        # Busca la palabra completa para evitar falsos positivos
        pattern = r"\b" + re.escape(kw.lower()) + r"\b"
        if re.search(pattern, text_lower):
            return True
    return False


def send_to_discord(video_url, title):
    """Envía la alerta al Webhook de Discord."""
    if not WEBHOOK_URL:
        print("Error: No se ha configurado la variable DISCORD_WEBHOOK_URL.")
        return False

    payload = {
        "content": f"@everyone \n**{title}**\n{video_url}",
        "username": "Alerta Dobshman",
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        WEBHOOK_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            if resp.status in (200, 204):
                print(f"Enviado a Discord con éxito: {title}")
                return True
            else:
                print(f"Respuesta inesperada de Discord ({resp.status})")
                return False
    except urllib.error.HTTPError as e:
        print(f"Error HTTP al enviar a Discord ({e.code}): {e.reason}")
    except Exception as e:
        print(f"Error enviando a Discord: {e}")

    return False


def main():
    channel_id = get_channel_id(HANDLE)
    if not channel_id:
        print(f"No se pudo determinar el Channel ID para {HANDLE}.")
        return

    print(f"Channel ID detectado: {channel_id}")
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    sent_videos = load_sent_videos()

    req = urllib.request.Request(
        rss_url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            xml_data = response.read()
    except Exception as e:
        print(f"Error obteniendo el feed RSS de YouTube: {e}")
        return

    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as e:
        print(f"Error al procesar el XML del feed: {e}")
        return

    ns = {
        "yt": "http://www.youtube.com/xml/schemas/2015",
        "atom": "http://www.w3.org/2005/Atom",
        "media": "http://search.yahoo.com/mrss/",
    }

    # Recorremos los vídeos en orden cronológico inverso (de más antiguos a más recientes)
    for entry in reversed(root.findall("atom:entry", ns)):
        video_id_elem = entry.find("yt:videoId", ns)
        title_elem = entry.find("atom:title", ns)
        link_elem = entry.find("atom:link", ns)

        if video_id_elem is None or title_elem is None or link_elem is None:
            continue

        video_id = video_id_elem.text
        title = title_elem.text
        video_url = link_elem.attrib.get("href", f"https://www.youtube.com/watch?v={video_id}")

        description_elem = entry.find("media:group/media:description", ns)
        description = (
            description_elem.text
            if description_elem is not None and description_elem.text
            else ""
        )

        if video_id in sent_videos:
            continue

        # Evaluación con expresiones regulares
        if matches_keywords(title, KEYWORDS) or matches_keywords(description, KEYWORDS):
            if send_to_discord(video_url, title):
                save_sent_video(video_id)
                sent_videos.add(video_id)


if __name__ == "__main__":
    main()
