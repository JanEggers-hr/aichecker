# hydrate.py
"""
Dieses Skript übernimmt das "Hydrieren" der Posts - die Links zu den Mediendaten
in den Posts werden heruntergeladen, damit sie im nächsten Schritt analysiert
werden können. Die Mediendateien werden in einem Verzeichnis abgelegt, 
in das der Server auch verlinken kann - so kann man das Tool zur Dokumentation
und Archivierung von Inhalten nutzen. 

Der Zugriff auf die Inhalte erfolgt asynchron, also parallelisiert. 

posts ist eine Liste von dict, die enthalten müssen: 
- 'id'
- 'media' (Liste von dict mit 'type' und 'url')
    - 'type' (z.B. 'image', 'video', 'voice')
    - 'url' (URL zur Mediendatei)

Gibt posts zurück, die Einträge in 'media' werden ergänzt um: 
- 'file' (Pfad zur heruntergeladenen Datei)
"""

SERVER_PATH = 'https://frankruft.de/ig-checks/media'

import os
import aiohttp
import asyncio
from .save_urls import save_url_async, save_url

async def hydrate_async(posts, mdir="./media"):
    # Liest die Files der Videos, Fotos, Voice-Messages asynchron ein. 
    async with aiohttp.ClientSession() as session:
        tasks = []
        for post in posts:
            i = 0
            if 'media' in post: 
                id = post['id']
                for m in post['media']: 
                    type = m['type']
                    url = m['url']
                    tasks.append(save_url_async(session, url, f"{id}_{type}_{i}", mdir))
                    i += 1
                    
        results = await asyncio.gather(*tasks)
        # Assign results back to posts
        index = 0
        for post in posts:
            if 'media' in post:
                for item in post['media']:
                    item['file'] = results[index]
                    index += 1

    return posts

# Hilfsfunktion: Alle Bild- und Medien-URL umbauen auf Server frankruft.de/ig-checks/media/{file}
def serverize(posts, server_path=SERVER_PATH):
    for post in posts:
        for m in post['media']:
            filename = os.path.basename(m['file'])
            m['file'] = server_path + "/" + filename
    return posts
