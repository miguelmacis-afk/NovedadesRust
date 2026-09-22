import json
import os
import urllib.request
import yt_dlp

# Configuración
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
  with open(DB_FILE, "r", encoding="utf-8") as f:
    return set(line.strip() for line in f if line.strip())


def save_sent_video(video_id):
  with open(DB_FILE, "a", encoding="utf-8") as f:
    f.write(f"{video_id}\n")


def send_to_discord(video_url, title):
  if not WEBHOOK_URL:
    print("Error: No se ha configurado DISCORD_WEBHOOK_URL")
    return False

  data = {
      "content": f"@everyone \n**{title}**\n{video_url}",
      "username": "Alerta Dobshman",
  }

  req = urllib.request.Request(WEBHOOK_URL, method="POST")
  req.add_header("Content-Type", "application/json")
  req.add_header("User-Agent", "Mozilla/5.0")

  try:
    urllib.request.urlopen(req, data=json.dumps(data).encode("utf-8"))
    print(f"Enviado a Discord: {title}")
    return True
  except Exception as e:
    print(f"Error enviando a Discord: {e}")
    return False


def fetch_latest_videos():
  ydl_opts = {
      "extract_flat": True,
      "skip_download": True,
      "quiet": True,
      "playlistend": 10,  # Revisa los 10 vídeos más recientes
  }

  videos = []
  try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
      info = ydl.extract_info(CHANNEL_URL, download=False)
      if "entries" in info:
        for entry in info["entries"]:
          if entry:
            v_id = entry.get("id")
            v_title = entry.get("title", "")
            v_url = (
                entry.get("url")
                or f"https://www.youtube.com/watch?v={v_id}"
            )
            videos.append({"id": v_id, "title": v_title, "url": v_url})
  except Exception as e:
    print(f"Error al obtener vídeos con yt-dlp: {e}")

  return videos


def main():
  sent_videos = load_sent_videos()
  videos = fetch_latest_videos()

  if not videos:
    print("No se pudieron obtener los vídeos del canal.")
    return

  # Procesar de más antiguo a más reciente
  for video in reversed(videos):
    video_id = video["id"]
    title = video["title"]
    video_url = video["url"]

    if video_id in sent_videos:
      continue

    title_lower = title.lower()
    if any(kw in title_lower for kw in KEYWORDS):
      if send_to_discord(video_url, title):
        save_sent_video(video_id)
        sent_videos.add(video_id)


if __name__ == "__main__":
  main()
