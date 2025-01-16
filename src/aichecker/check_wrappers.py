from .detectora import query_detectora
# from .aiornot import query_aiornot
from .transcribe import gpt4_description
import logging

# Alternative zu meinen selbst geschriebenen aiornot-Routinen: 
# https://github.com/aiornotinc/aiornot-python
# Installieren mit
#    pip install aiornot

from aiornot import Client

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
            'confidence': response.report.ai.confidence if hasattr(response.report, 'ai') else .99,
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