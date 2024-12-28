# imagecheck.py
# Erfragt KI-Wahrscheinlichkeit für ein Bild über Hive- und AIorNot-API
from bildbeschreibung import ai_description

import requests
import json
import os

# Konstanten #
endpoint_url = "https://api.aiornot.com/v1/reports/image"

def query_aiornot(image):
    # Erwartet URI eines Bildes
    # AIORNot-API-Dokumentation: https://docs.aiornot.com/
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
            return response.json()['report']['verdict']
        elif response.status_code == 400:
            print("AIORNOT: Fehlerhafte API-Anfrage")
            return None
        elif response.status_code == 401:
            print(f"AIORNOT-API-Key 'api_key' nicht gültig")
    except Exception as e:
        print("Fehler beim Verbinden mit der AIORNOT-API:", str(e))
        return None
    return response['']
    
