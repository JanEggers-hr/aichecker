# detectora.py Library - CC-BY github.com/JanEggers-hr
"""
Spinoff einer Masterarbeit von Tom Tlok. Letzten Endes ein feingetuntes und gegen 
Angriffe gehärtetes BERT, das vor allem auf die sehr KI-typischen Eigenheiten in 
Satzbau und Wortwahl zu achten scheint. Trainiert auf die gängigen Modelle.
Mehr hier: https://ki.fh-wedel.de/files/TomTlok_MA.pdf 

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
import logging

# os.environ.get('OPENAI_API_KEY')

# Konstanten #
api_url = "https://backendkidetektor-apim.azure-api.net/watson"

def query_detectora(text):
    if text == '':
        return None
    logging.info(f"Checke Text mit Detectora: {text[:20]}...")
    data = {
        'query': text,
    }
    api_key = os.environ.get('DETECTORA_API_KEY')
    if api_key is None or api_key == "":
        logging.error("DETECTORA_API_KEY ist nicht gesetzt")
        return None
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
            logging.error(f"DETECTORA: Fehlerhafte API-Anfrage: \'{data['query']}\'")
            return None
        elif response.status_code == 401:
            logging.error(f"DETECTORA_API_KEY {api_key} nicht gültig")
            return None
    except Exception as e:
        logging.error("Fehler beim Verbinden mit der DETECTORA-API:", str(e))
        return None
    
