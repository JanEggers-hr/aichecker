# imagecheck.py
# Erfragt KI-Wahrscheinlichkeit für ein Bild über Hive- und AIorNot-API
from .transcribe import ai_description

import requests
import json
import os
import time

# Konstanten #
endpoint_url = "https://api.aiornot.com/v1/reports/image"

def query_aiornot(image):
    # Erwartet URI eines Bildes.
    # Derzeit kann die AIORNOT-API keine base64-Bilder verarbeiten; d.h.: Eine URI der Form
    # "data:image/jpeg;base64, ..." führt zu einem 400-Fehler. 
    # (Also in diesem Fall: Datei abspeichern und über files= hochladen. )
    #
    # Wichtigste Rückgabewerte im dict: 
    # - 'verdict' ('human' oder 'ai')
    # - 'ai'/'confidence' (wie sicher ist sich das Modell?)
    # - 'generator' ist ein dict, das für die vier geprüften Modelle 
    #   'dall_e', 'stable_diffusion', 'this_person_does_not_exist' und 'midjourney' 
    #   jeweils einen 'confidence'-Wert angibt. 
    # 
    # AIORNot-API-Dokumentation: https://docs.aiornot.com/#5b3de85d-d3eb-4ad1-a191-54988f56d978
    
    data = json.dumps({
        'object': image,
    })
    api_key = os.environ.get('AIORNOT_API_KEY')
    headers = {
        'Authorization': f"Bearer {api_key}",
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    # Base64-Datei? Temporären File abspeichern und über files= hochladen
    if image.startswith("data:image/"):
        headers = {
            'Authorization': f"Bearer {api_key}",
            'Accept': 'application/json',
        }   
        fname = save_string_to_temp(image)
        try:
            response = requests.post(endpoint_url,
                                     headers=headers,
                                     files={'object': open(fname, 'rb')})
            
        except Exception as e:
            print("Fehler beim Verbinden mit der AIORNOT-API über multipart:", str(e))
            return None
    try: 
        response = requests.post(endpoint_url,
                                headers=headers,
                                data=data
                                )
    except Exception as e:
        print("Fehler beim Verbinden mit der AIORNOT-API:", str(e))
        return None
    if response.status_code == 200:
        # Success
        return response.json()['report']
    elif response.status_code == 400:
        print("AIORNOT: Fehlerhafte API-Anfrage")
        return None
    elif response.status_code == 401:
        print(f"AIORNOT-API-Key 'api_key' nicht gültig")
        return None
    elif response.status_code == 429: 
        # Zu viele Anfragen; also warten und nochmal fragen
        time.sleep(1)
        response = requests.post(endpoint_url,
                            headers=headers,
                            data=data
                            )
        # Immer noch 429? Dann sind wahrscheinlich die Credits aufgebraucht
        if response.status_code == 429:
            print("AIORNOT: Credits verbraucht")
            return None
        else:
            return response.json()['report']
    return None
    
# Hilfsfunktion: base64 als Temp-File speichern
import base64

# Example base64 image string: "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD..."
def save_string_to_temp(image, fname="./temp"):
    header, encoded = image.split(",", 1)
    # Leerzeichen entfernen
    while encoded[0] == " ":
        encoded = encoded[1:]
    # Step 2: Decode the base64 string to get the binary image data
    image_data = base64.b64decode(encoded) 
    # Step 3: Write the binary data to a file
    # Extract the file extension from the header
    file_extension = header.split(";")[0].split("/")[1]
    file_name = f"{fname}.{file_extension}"
    with open(file_name, "wb") as image_file:
        image_file.write(image_data)
    return file_name