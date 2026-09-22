import json
import os
import re
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


def get_channel_id(handle):
  """Obtiene el ID oficial 'UC...' directamente desde la página del canal."""
  url = f"https://www.youtube.com/{handle}"
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
      )
  }
  req = urllib.request.Request(url, headers=headers)
  try:
    with urllib.request.urlopen(req) as resp:
      html = resp.read().decode("utf-8")
      match = re.search(r'"channelId":"(UC[a-zA-Z0-9_-]{22})"', html)
      if match:
        return match.group(1)
  except Exception as e:
    print(f"Error al resolver el ID del canal para {handle}: {e}")
  return None


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


def main():
  channel_id = get_channel_id(HANDLE)
  if not channel_id:
    print(f"No se pudo determinar el Channel ID para {HANDLE}.")
    return

  rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
  sent_videos = load_sent_videos()

  req = urllib.request.Request(
      rss_url,
      headers={
          "User-Agent": (
              "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
          )
      },
  )

  try:
    response = urllib.request.urlopen(req)
    xml_data = response.read()
  except Exception as e:
    print(f"Error obteniendo el feed de YouTube: {e}")
    return

  root = ET.fromstring(xml_data)
  ns = {
      "yt": "http://www.youtube.com/xml/schemas/2015",
      "atom": "http://www.w3.org/2005/Atom",
      "media": "http://search.yahoo.com/mrss/",
  }

  for entry in reversed(root.findall("atom:entry", ns)):
    video_id = entry.find("yt:videoId", ns).text
    title = entry.find("atom:title", ns).text
    video_url = entry.find("atom:link", ns).attrib["href"]

    description_elem = entry.find("media:group/media:description", ns)
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
