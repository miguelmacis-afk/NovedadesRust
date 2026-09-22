import json
import os
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

# Datos del canal verificados
CHANNEL_HANDLE = "Dobshman"
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
TIMEOUT = 15


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
    if not text:
        return False
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


def extract_videos_from_json(obj, video_list):
    """Recorre recursivamente el objeto ytInitialData para extraer los renderizadores de vídeo."""
    if isinstance(obj, dict):
        if "videoRenderer" in obj:
            vr = obj["videoRenderer"]
            video_id = vr.get("videoId")
            title = ""
            if "title" in vr:
                if "runs" in vr["title"]:
                    title = "".join(
                        r.get("text", "")
                        for r in vr["title"]["runs"]
                        if "text" in r
                    )
                elif "simpleText" in vr["title"]:
                    title = vr["title"]["simpleText"]

            description = ""
            if "descriptionSnippet" in vr and "runs" in vr["descriptionSnippet"]:
                description = "".join(
                    r.get("text", "")
                    for r in vr["descriptionSnippet"]["runs"]
                    if "text" in r
                )

            if video_id and title:
                video_list.append(
                    {
                        "id": video_id,
                        "title": title,
                        "url": f"https://www.youtube.com/watch?v={video_id}",
                        "description": description,
                    }
                )
        else:
            for value in obj.values():
                extract_videos_from_json(value, video_list)
    elif isinstance(obj, list):
        for item in obj:
            extract_videos_from_json(item, video_list)


def fetch_videos_by_web_scrape(handle):
    """Consulta la página web del canal (@Dobshman/videos) directamente. Inmune al bloqueo 404 de RSS."""
    url = f"https://www.youtube.com/@{handle}/videos"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        # Buscar los datos estructurados en la página
        match = re.search(r"ytInitialData\s*=\s*({.*?});</script>", html)
        if not match:
            match = re.search(
                r'window\["ytInitialData"\]\s*=\s*({.*?});</script>', html
            )

        if match:
            data = json.loads(match.group(1))
            extracted = []
            extract_videos_from_json(data, extracted)

            # Deduplicar preservando el orden
            seen = set()
            unique_videos = []
            for item in extracted:
                if item["id"] not in seen:
                    seen.add(item["id"])
                    unique_videos.append(item)

            if unique_videos:
                print(
                    f"Obtenidos {len(unique_videos)} vídeos mediante scraping de la página del canal."
                )
                return unique_videos
    except Exception as e:
        print(f"Error al raspar la página del canal: {e}")

    return None


def fetch_videos_by_rss(channel_id):
    """Método de respaldo mediante el feed RSS estándar."""
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            xml_data = resp.read()

        root = ET.fromstring(xml_data)
        ns = {
            "yt": "http://www.youtube.com/xml/schemas/2015",
            "atom": "http://www.w3.org/2005/Atom",
            "media": "http://search.yahoo.com/mrss/",
        }

        videos = []
        for entry in root.findall("atom:entry", ns):
            v_id = entry.find("yt:videoId", ns)
            v_title = entry.find("atom:title", ns)
            v_link = entry.find("atom:link", ns)

            if v_id is not None and v_title is not None:
                video_id = v_id.text
                title = v_title.text
                url_str = (
                    v_link.attrib.get("href")
                    if v_link is not None
                    else f"https://www.youtube.com/watch?v={video_id}"
                )

                desc_elem = entry.find("media:group/media:description", ns)
                desc = desc_elem.text if desc_elem is not None else ""

                videos.append(
                    {
                        "id": video_id,
                        "title": title,
                        "url": url_str,
                        "description": desc,
                    }
                )

        if videos:
            print(f"Obtenidos {len(videos)} vídeos mediante feed RSS.")
            return videos
    except Exception as e:
        print(f"Aviso: El feed RSS devolvió error ({e}).")

    return None


def main():
    print(f"Consultando canal: @{CHANNEL_HANDLE} ({CHANNEL_ID})")

    # 1. Intentar obtención directa vía scraping de la página de vídeos
    videos = fetch_videos_by_web_scrape(CHANNEL_HANDLE)

    # 2. Si falla la web, usar como respaldo el RSS
    if not videos:
        videos = fetch_videos_by_rss(CHANNEL_ID)

    if not videos:
        print("Error: No se pudo obtener la lista de vídeos de ninguna fuente.")
        return

    sent_videos = load_sent_videos()

    # Procesar de los vídeos más antiguos a los más recientes
    for item in reversed(videos):
        video_id = item["id"]
        title = item["title"]
        video_url = item["url"]
        description = item.get("description", "")

        if video_id in sent_videos:
            continue

        if matches_keywords(title, KEYWORDS) or matches_keywords(
            description, KEYWORDS
        ):
            if send_to_discord(video_url, title):
                save_sent_video(video_id)
                sent_videos.add(video_id)


if __name__ == "__main__":
    main()
