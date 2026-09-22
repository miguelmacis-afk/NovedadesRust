import json
import os
import re
import urllib.request

# Configuración del canal de Dobshman
CHANNEL_URL = "https://www.youtube.com/@Dobshman/videos"
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
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
      " like Gecko) Chrome/120.0.0.0 Safari/537.36",
  )

  try:
    urllib.request.urlopen(req, data=json.dumps(data).encode("utf-8"))
    print(f"Enviado a Discord: {title}")
    return True
  except Exception as e:
    print(f"Error enviando a Discord: {e}")
    return False


def main():
  sent_videos = load_sent_videos()

  req = urllib.request.Request(
      CHANNEL_URL,
      headers={
          "User-Agent": (
              "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
              " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
          ),
          "Accept-Language": "es-ES,es;q=0.9",
      },
  )

  try:
    with urllib.request.urlopen(req) as response:
      html_content = response.read().decode("utf-8")
  except Exception as e:
    print(f"Error obteniendo la página de YouTube: {e}")
    return

  # Patrón para extraer IDs de videos y títulos incrustados en el JSON de la página de YouTube
  # Busca coincidencias del tipo {"videoId":"XXXXXXXXXXX","title":{"runs":[{"text":"..."}]}}
  pattern = re.r_compile(
      r'{"videoId":"([a-zA-Z0-9_-]{11})",.*?"title":\{"runs":\[\{"text":"([^"]+)"'
  )

  matches = re.findall(
      r'"videoId":"([a-zA-Z0-9_-]{11})".*?"title":\{"runs":\[\{"text":"([^"]+)"',
      html_content,
  )

  if not matches:
    # Intento alternativo de patrón por si cambia la estructura de YouTube
    matches = re.findall(
        r'"videoId":"([a-zA-Z0-9_-]{11})".*?"accessibility":\{"accessibilityData":\{"label":"([^"]+)"',
        html_content,
    )

  processed_ids = set()

  for video_id, title in matches:
    if video_id in processed_ids:
      continue
    processed_ids.add(video_id)

    if video_id in sent_videos:
      continue

    video_url = f"https://www.youtube.com/watch?v={video_id}"
    title_lower = title.lower()

    # Comprobación de palabras clave solo en el título (más seguro mediante scraping HTML)
    if any(kw in title_lower for kw in KEYWORDS):
      if send_to_discord(video_url, title):
        save_sent_video(video_id)
        sent_videos.add(video_id)


if __name__ == "__main__":
  main()
