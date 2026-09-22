import json
import os
import time
import urllib.request
import xml.etree.ElementTree as ET

# Configuración del canal de Dobshman
CHANNEL_ID = "UC4pncBlim9VvDbWXXBgo5KA"
# Usamos una instancia pública de Invidious para el feed RSS (evita el bloqueo 404 de YouTube)
RSS_URL = f"https://invidious.nerdvpn.de/feed/channel/{CHANNEL_ID}"

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


def load_sent_videos():
  if not os.path.exists(DB_FILE):
    return set()
  with open(DB_FILE, "r") as f:
    return set(line.strip() for line in f if line.strip())


def save_sent_video(video_id):
  with open(DB_FILE, "a") as f:
    f.write(f"{video_id}\n")


def send_to_discord(video_url, title):
  if not WEBHOOK_URL:
    print("No se ha configurado DISCORD_WEBHOOK_URL")
    return False

  data = {
      "content": f"@everyone \n**{title}**\n{video_url}",
      "username": "Alerta Dobshman",
  }

  req = urllib.request.Request(WEBHOOK_URL, method="POST")
  req.add_header("Content-Type", "application/json")
  req.add_header(
      "User-Agent",
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
  )

  try:
    urllib.request.urlopen(req, data=json.dumps(data).encode("utf-8"))
    print(f"Enviado a Discord: {title}")
    return True
  except Exception as e:
    print(f"Error enviando a Discord: {e}")
    return False


def fetch_rss_with_retries(url, retries=3, delay=5):
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
      ),
      "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
  }

  for attempt in range(1, retries + 1):
    try:
      req = urllib.request.Request(url, headers=headers)
      with urllib.request.urlopen(req) as response:
        return response.read()
    except Exception as e:
      print(f"Intento {attempt}/{retries} fallido al obtener el feed: {e}")
      if attempt < retries:
        print(f"Reintentando en {delay} segundos...")
        time.sleep(delay)
      else:
        return None


def main():
  sent_videos = load_sent_videos()

  xml_data = fetch_rss_with_retries(RSS_URL)
  if not xml_data:
    print("No se pudo obtener el feed alternativo.")
    return

  try:
    root = ET.fromstring(xml_data)
  except Exception as e:
    print(f"Error al parsear el XML: {e}")
    return

  ns = {
      "yt": "http://www.youtube.com/xml/schemas/2015",
      "atom": "http://www.w3.org/2005/Atom",
      "media": "http://search.yahoo.com/mrss/",
  }

  # Invidious / Atom estándar
  for entry in reversed(root.findall("atom:entry", ns)):
    id_elem = entry.find("atom:id", ns)
    if id_elem is not None and ":" in id_elem.text:
      video_id = id_elem.text.split(":")[-1]
    else:
      continue

    title_elem = entry.find("atom:title", ns)
    title = title_elem.text if title_elem is not None else ""

    link_elem = entry.find("atom:link", ns)
    video_url = (
        link_elem.attrib.get("href")
        if link_elem is not None
        else f"https://www.youtube.com/watch?v={video_id}"
    )

    description_elem = entry.find("media:group/media:description", ns)
    if description_elem is None:
      description_elem = entry.find("atom:content", ns)
    description = (
        description_elem.text
        if description_elem is not None and description_elem.text
        else ""
    )

    if video_id in sent_videos:
      continue

    title_lower = title.lower()
    desc_lower = description.lower()

    if any(kw in title_lower or kw in desc_lower for kw in KEYWORDS):
      if send_to_discord(video_url, title):
        save_sent_video(video_id)
        sent_videos.add(video_id)


if __name__ == "__main__":
  main()
