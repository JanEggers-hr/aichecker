from .detectora import query_detectora
from .aiornot import query_aiornot
from .transcribe import gpt4_description

# Konstante 
d_thresh = .8 # 80 Prozent 
limit = 25 # Posts für den Check

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
    # Verpackung. Fortschrittsbalken.
    if content is None:
        print(" ", end="")
        return
    # Fortschrittsbalken
    print("?", end="")
    report = query_aiornot(content, is_image)
    # Beschreibung: https://docs.aiornot.com/#5b3de85d-d3eb-4ad1-a191-54988f56d978   
    if report is not None:  
        aiornot_dict = ({
            'aiornot_score': report['verdict'],
            # Unterscheidung: Bilder haben den Confidence score im Unter-Key 'ai'
            'aiornot_confidence': report['ai']['confidence'] if 'ai' in report else report['confidence'],
            'aiornot_generator': report['generator'] if 'generator' in report else 'Audio',
        })
        print(f"\b{'X' if aiornot_dict['aiornot_score'] != 'human' else '.'}",end="")
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
        for i in images:
            # Construct an URL for the image thumbnail (normalised size)
            link = i['image']['ref']['$link']
            i_url = f"https://cdn.bsky.app/img/feed_thumbnail/plain/{did}/{link}"
            aiornot_report = aiornot_wrapper(i_url)
            aiornot_report['gpt4_description'] = gpt4_description(image)
            desc.append(aiornot_report)
        return desc
    else:
        print("\b_",end="")
        return None