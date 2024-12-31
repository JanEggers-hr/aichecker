# imagecheck.py
# Erfragt KI-Wahrscheinlichkeit für ein Bild über Hive- und AIorNot-API
from .bildbeschreibung import ai_description

import requests
import json
import os
import time

# Konstanten #
endpoint_url = "https://api.aiornot.com/v1/reports/image"

def query_aiornot(image):
    # Erwartet URI eines Bildes
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
    try: 
        response = requests.post(endpoint_url,
                                headers=headers,
                                data=data
                                )
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
    except Exception as e:
        print("Fehler beim Verbinden mit der AIORNOT-API:", str(e))
        return None
    return None
    
