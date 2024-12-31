# detectora.py Library - CC-BY github.com/JanEggers-hr
"""
Eine Python-Bibliothek, um mit detectora.de auf KI-generierten Text zu prüfen. 

PARAMETER: text
Erwartet einen Text-Chunk, gibt die die Wahrscheinlichkeit zurück, dass der Text KI-generiert ist.

Achtung: Führt kein Chunking durch. Texte sollten also nicht zu lang werden. (Token-Länge
des Modells: ?)

RÜCKGABEWERT: real
Gibt die Wahrscheinlichkeit zurück, die das Modell dem Text zuweist (zwischen 0 und 1)

Detectora-Key muss als DETECTORA_API_KEY in .env hinterlegt sein. 
"""

import requests
import json
import os

# os.environ.get('OPENAI_API_KEY')

# Konstanten #
api_url = "https://backendkidetektor-apim.azure-api.net/watson"

def query_detectora(text):
    if text == '':
        return None
    data = {
        'query': text,
    }
    api_key = os.environ.get('DETECTORA_API_KEY')
    headers = {
        'APIKey': api_key,
        'Content-Type': 'application/json',
    }
    try: 
        response = requests.post(api_url,
                                headers=headers,
                                json=data
                                )
        if response.status_code == 200:
            # Success
            return response.json()['fake_probability']
        elif response.status_code == 400:
            print(f"DETECTORA: Fehlerhafte API-Anfrage: \'{data['query']}\'")
            return None
        elif response.status_code == 401:
            print(f"DETECTORA-API-Key 'api_key' nicht gültig")
    except Exception as e:
        print("Fehler beim Verbinden mit der DETECTORA-API:", str(e))
        return None
    return response['']
    
