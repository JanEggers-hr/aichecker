import logging
import re
import os
import requests
import aiofiles



## Abspeichern in Dateien

def save_url(fname, name, mdir):
    # Die Medien-URLs bekommen oft einen Parameter mit übergeben; deswegen nicht nur
    # "irgendwas.ogg" berücksichtigen, sondern auch "irgendwas.mp4?nochirgendwas"
#    mdir = os.path.dirname(os.path.abspath(__file__)) + '/../media'
    mdir = "./media"
    content_ext = re.search(r"\.[a-zA-Z0-9]+(?=\?|$)",fname).group(0)
    content_file = f"{mdir}/{name}{content_ext}"
    try:
        os.makedirs(os.path.dirname(content_file), exist_ok=True)
    except:
        logging.error(f"Kann kein Media-Directory in {mdir} öffnen")
        return None
    try:
        with open(content_file, 'wb') as f:
            f.write(requests.get(fname).content)
        return content_file
    except:
        logging.error(f"Kann Datei {content_file} nicht schreiben")
        return None
    
async def save_url_async(session, fname, name, mdir):
    # Die Medien-URLs bekommen oft einen Parameter mit übergeben; deswegen nicht nur
    # "irgendwas.ogg" berücksichtigen, sondern auch "irgendwas.mp4?nochirgendwas"
    # mdir = os.path.dirname(os.path.abspath(__file__)) + '/../media'
    content_ext = re.search(r"\.[a-zA-Z0-9]+(?=\?|$)", fname).group(0)
    content_file = f"{mdir}/{name}{content_ext}"
    try:
        os.makedirs(os.path.dirname(content_file), exist_ok=True)
    except Exception as e:
        logging.error(f"Kann kein Media-Directory in {mdir} öffnen: {e}")
        return None
    try:
        async with session.get(fname) as response:
            content = await response.read()
            async with aiofiles.open(content_file, 'wb') as f:
                await f.write(content)
        return content_file
    except Exception as e:
        logging.error(f"Kann Datei {content_file} nicht schreiben: {e}")
        return None