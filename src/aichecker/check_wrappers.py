from .detectora import query_detectora
# from .aiornot import query_aiornot
from .transcribe import gpt4_description
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
import requests 

# Alternative zu meinen selbst geschriebenen aiornot-Routinen: 
# https://github.com/aiornotinc/aiornot-python
# Installieren mit
#    pip install aiornot

from aiornot import Client, AsyncClient

# Konstante 
d_thresh = .8 # 80 Prozent 
limit = 25 # Posts für den Check

def object_to_dict(obj):
    """Recursively converts an object to a dictionary."""
    if isinstance(obj, dict):
        # Recursively handle dictionaries
        return {k: object_to_dict(v) for k, v in obj.items()}
    elif hasattr(obj, "__dict__"):
        # Handle objects with __dict__
        return {k: object_to_dict(v) for k, v in vars(obj).items()}
    elif isinstance(obj, (list, tuple, set)):
        # Handle iterables
        return type(obj)(object_to_dict(v) for v in obj)
    else:
        # Return the object if it cannot be converted
        return obj

def detectora_wrapper(text: str):
    # Verpackung. Fügt nur den "Fortschrittsbalken" hinzu. 
    print("?", end="")
    if text is None:
        print("\b_",end="")
        return None
    score = query_detectora(text)
    if score is None:
        print("\b_",end="")
    else: 
        print(f"\b{'X' if score >= d_thresh else '.'}",end="")
    return score

def aiornot_wrapper(content, is_image = True):
    aiornot_client = Client()
    # Verpackung. Fortschrittsbalken.
    if content is None:
        print(" ", end="")
        return
    # Fortschrittsbalken
    print("?", end="")
    is_url = (content.startswith("http://") or content.startswith("https://"))
    if is_image:
        try:
            response = aiornot_client.image_report_by_url(content) if is_url else aiornot_client.image_report_by_file(content)
        except Exception as e: 
            logging.error(f"AIORNOT-Image-API-Fehler: {e}")
            return None
    else: 
        # Achtung: DERZEIT (13.1.25) verarbeitet die Audio-API nur MP3-Dateien, keine MP4/M4A.
        # Und Ogg schon gleich zweimal nicht. 
        # Sie gibt auch noch keinen Confidence-Wert zurück, anders als dokumentiert.
        try:
            response = aiornot_client.audio_report_by_url(content) if is_url else aiornot_client.audio_report_by_file(content)        
        except Exception as e:
            logging.error(f"AIORNOT-Audio-API-Fehler: {e}")
            return None           
    # Beschreibung: https://docs.aiornot.com/#5b3de85d-d3eb-4ad1-a191-54988f56d978   
    if response is not None:  
        aiornot_dict = ({
            'score': response.report.verdict,
            # Unterscheidung: Bilder haben den Confidence score im Unter-Key 'ai'
            # Audios SOLLTEN eien Confidence-Wert in response.report.confidence haben, haben es aber nicht
            'confidence': response.report.ai.confidence if hasattr(response.report, 'ai') else 1.01,
            'generator': object_to_dict(response.report.generator) if hasattr(response.report, 'generator') else None,
        })
        print(f"\b{'X' if aiornot_dict['score'] != 'human' else '.'}",end="")
        return aiornot_dict
    else:
        print("\b,")
        return None
        
def bsky_aiornot_wrapper(did,embed):
    # Verpackung für die AIORNOT-Funktion: 
    # Checkt, ob es überhaupt ein Embed gibt, 
    # und ob es ein Bild enthält.
    # Wenn ja: geht durch die Bilder und erstellt KI-Beschreibung und KI-Einschätzung
    if 'images' in embed:
        images = embed['images']
        desc = []
        for image in images:
            # Construct an URL for the image thumbnail (normalised size)
            link = image['image']['ref']['$link']
            i_url = f"https://cdn.bsky.app/img/feed_thumbnail/plain/{did}/{link}"
            aiornot_report = aiornot_wrapper(i_url)
            aiornot_report['gpt4_description'] = gpt4_description(i_url)
            desc.append(aiornot_report)
        return desc
    else:
        print("\b_",end="")
        return None
    
    
    # Wrapper für Describe und transcribe aus transcribe.py
# Parallelisieren von eigentlich synchronen Routinen: Aufruf in ThreadPoolExecutor einklinken
async def describe_async(image_data):
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        result = await loop.run_in_executor(pool, gpt4_description, image_data)
    return result

async def transcribe_async(file):
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        result = await loop.run_in_executor(pool, transcribe, file)
    return result

# Wrapper für AIORNOT-Check
# Das ist im Augenblick ein wenig geschummelt; es gibt ja eine asynchrone AIORNOT-Routine. 
# Die baue ich im nächsten Schritt ein. 
async def aiornot_async(file, is_image=True):
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        result = await loop.run_in_executor(pool, aiornot_wrapper, file, is_image)
    return result

# Wrapper für Detectora-Check
# Auch hier könnte man unter der Oberfläche einen parallelisierbaren API-Aufruf bauen. 
async def detectora_async(text):
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        result = await loop.run_in_executor(pool, detectora_wrapper, text)
    return result

# Hive-Detektor-Aufruf, einmal synchron und einmal asynchron. 
# Gibt ein dict zurück: 
# {
#   'ai_score': real,
#   'most_likely_model': string,
#   'models': [ {'class': string, 'score': real}, ... ]
# }
def hive_visual(content):
    url = 'https://api.thehive.ai/api/v2/task/sync'
    api_key = os.environ.get('HIVE_VISUAL_API_KEY')
    if api_key is None or api_key == "":
        logging.error("Kein API-Key für Hive Visual Detection")
        return None
    headers = {'Authorization': f"Token {api_key}"}
    if content.startswith("http://") or content.startswith("https://"):
        data= {'url': content}
        response = requests.post(url, headers=headers, data=data)
        response = response.json()
    else: 
        # Datei als Input
        try:
            binary = open(content, 'rb')
        except FileNotFoundError:
            logging.error(f"Datei {content} nicht gefunden")
            return None
        files = {'image': binary}
        response = requests.post(url, headers=headers, files=files)
        response = response.json()
        scores = response.output.classes
        score = {'models': []}
        max = 0
        for s in scores: 
            if s['class'] == 'ai_generated':
                score['ai_score'] = s['score']
            else:
                score['models'].append(s)
                if s['score'] > max:
                    max = s['score']
                    score['most_likely_model'] = s['class']
        return score

# Hive-Check Visual Content
# Parallelisiert
async def hive_visual_async(session, content):
    url = 'https://api.thehive.ai/api/v2/task/sync'
    api_key = os.environ.get('HIVE_VISUAL_API_KEY')
    if api_key is None or api_key == "":
        logging.error("Kein API-Key für Hive Visual Detection")
        return None
    headers = {'Authorization': f"Token {api_key}"}
    if content.startswith("http://") or content.startswith("https://"):
        data = {'url': content}
        async with session.post(url, headers=headers, data=data) as response:
            response = await response.json()
            return response
    # Datei als Input
    else:
        try: 
            binary = open('content', 'rb')
        except FileNotFoundError:
            logging.error(f"Datei {content} nicht gefunden")
            return None
        files = {'image': binary}
        async with session.post(url, headers=headers, files=files, data=data) as response:
            response = await response.json()
            # Eine List of dicts zurückgeben, die so aufgebaut ist: 
            # [{'class': class, 'score': confidence}, ...]
            # Die erste ist: {'class': 'ai_generated', 'score': score}
            scores = response.output.classes
            score = {'models': []}
            max = 0
            for s in scores: 
                if s['class'] == 'ai_generated':
                    score['ai_score'] = s['score']
                else:
                    score['models'].append(s)
                    if s['score'] > max:
                        max = s['score']
                        score['most_likely_model'] = s['class']
            return score
    return None    