import json
import os
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

# ==========================================
# CONFIGURACIÓN
# ==========================================
# Reemplaza este valor con el Channel ID real obtenido en el paso anterior
CHANNEL_ID = "UC4pncBlim9VvDbWXXBgo5KA" 

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
TIMEOUT = 10


def load_sent_videos():
    if not os.path.exists(DB_FILE):
        return set()
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    except IOError as e:
        print(f"Error al leer {DB_FILE}: {e}")
        return set()


def save_sent_video(video_id):
    try:
        with open(DB_FILE, "a", encoding="utf-8") as f:
            f.write(f"{video_id}\n")
    except IOError as e:
        print(f"Error al guardar el ID {video_id} en {DB_FILE}: {e}")


def matches_keywords(text, keywords):
    text_lower = text.lower()
    for kw in keywords:
        pattern = r"\b" + re.escape(kw.lower()) + r"\b"
        if re.search(pattern, text_lower):
            return True
    return False


def send_to_discord(video_url, title):
    if not WEBHOOK_URL:
        print("Error: No se ha configurado DISCORD_WEBHOOK_URL")
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
    except Exception as e:
        print(f"Error enviando a Discord: {e}")

    return False


def main():
    if not CHANNEL_ID or CHANNEL_ID.startswith("UC_AQUÍ"):
        print("Error: Debes poner el CHANNEL_ID real en el script.")
        return

    print(f"Consultando feed RSS para el canal: {CHANNEL_ID}")
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"
    sent_videos = load_sent_videos()

    req = urllib.request.Request(
        rss_url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
    )

    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            xml_data = response.read()
    except urllib.error.HTTPError as e:
        print(f"Error HTTP obteniendo el feed RSS ({e.code}): Comprueba que el CHANNEL_ID sea correcto.")
        return
    except Exception as e:
        print(f"Error de conexión obteniendo el feed: {e}")
        return

    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as e:
        print(f"Error al procesar el XML: {e}")
        return

    ns = {
        "yt": "http://www.youtube.com/xml/schemas/2015",
        "atom": "http://www.w3.org/2005/Atom",
        "media": "http://search.yahoo.com/mrss/",
    }

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

        if matches_keywords(title, KEYWORDS) or matches_keywords(description, KEYWORDS):
            if send_to_discord(video_url, title):
                save_sent_video(video_id)
                sent_videos.add(video_id)


if __name__ == "__main__":
    main()
