import os
import json
import urllib.request
import xml.etree.ElementTree as ET

# Configuración
CHANNEL_ID = "UC4pncBlim9VvDbWXXBgo5KA" # ID extraído del canal @Triko_ez
RSS_URL = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
KEYWORDS = ["drop", "forced", "forzado", "actualizacion", "actualización", "update"]
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
        "username": "Alerta Dobshman"
    }
   
    req = urllib.request.Request(WEBHOOK_URL, method="POST")
    req.add_header('Content-Type', 'application/json')
    req.add_header('User-Agent', 'Mozilla/5.0')
    
    try:
        urllib.request.urlopen(req, data=json.dumps(data).encode('utf-8'))
        print(f"Enviado a Discord: {title}")
        return True
    except Exception as e:
        print(f"Error enviando a Discord: {e}")
        return False

def main():
    sent_videos = load_sent_videos()
    
    req = urllib.request.Request(RSS_URL, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        response = urllib.request.urlopen(req)
        xml_data = response.read()
    except Exception as e:
        print(f"Error obteniendo el feed de YouTube: {e}")
        return

    root = ET.fromstring(xml_data)
    ns = {'yt': 'http://www.youtube.com/xml/schemas/2015', 'atom': 'http://www.w3.org/2005/Atom', 'media': 'http://search.yahoo.com/mrss/'}
    
    # Buscar todos los vídeos del feed
    for entry in reversed(root.findall('atom:entry', ns)):
        video_id = entry.find('yt:videoId', ns).text
        title = entry.find('atom:title', ns).text
        video_url = entry.find('atom:link', ns).attrib['href']
        
        # Extraer descripción si existe
        description_elem = entry.find('media:group/media:description', ns)
        description = description_elem.text if description_elem is not None and description_elem.text else ""
        
        if video_id in sent_videos:
            continue # Se salta si ya fue enviado
            
        title_lower = title.lower()
        desc_lower = description.lower()
        
        # Filtrar por palabras clave en título o descripción
        if any(kw in title_lower or kw in desc_lower for kw in KEYWORDS):
            if send_to_discord(video_url, title):
                save_sent_video(video_id)
                sent_videos.add(video_id)

if __name__ == "__main__":
    main()
