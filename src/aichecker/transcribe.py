# transcribe.py
#
# Bilder mit GPT4o-mini in Bildbeschreibung umwandeln, 
# Audios/Videos lokal mit whisper transkribieren

import ollama
from openai import OpenAI
from pathlib import Path
import os
import whisper

prompt = """Du bist Barrierefreiheits-Assistent.
Du erstellst eine deutsche Bildbeschreibung für den Alt-Text.
Beschreibe, was auf dem Bild zu sehen ist.
Beginne sofort mit der Beschreibung. Sei präzise und knapp.
Du erstellst eine deutsche Bildbeschreibung für den Alt-Text.  
Beschreibe, was auf dem Bild zu sehen ist. 
Beginne sofort mit der Beschreibung. Sei präzise und knapp. 
Wenn das Bild lesbaren Text enthält, zitiere diesen Text."""
client = OpenAI(api_key = os.environ.get('OPENAI_API_KEY'))
# Use GPT-4 mini to describe images
OLLAMA = False

def gpt4_description(image_url):
    # Check a local image by converting it to b64: 
    # image_url = f"data:image/jpeg;base64,{b64_image}"
    response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url":  image_url,
                            }
                        },
                    ],
                }
            ],
            max_tokens=300,
        )
    return response.choices[0].message.content

def llama_description(b64_image):
    response = ollama.chat(
        model="llama3.2-vision",
        messages=[{
            'role': 'user',
            'content': prompt,
            'images': [b64_image]
            }]
        )
    return response['message']['content'].strip()


def ai_description(image):
    if OLLAMA:
        desc2 = llama_description(image)
    else:
        desc2 = gpt4_description(image)
        desc2 = gpt4_description(image) 
    # Return ai-generated description
    return desc2

def transcribe(audio):
    # Wrapper; ruft eine der drei Whisper-Transcribe-Varianten auf. 
    # Favorit: das beschleunigte whisper-s2t
    # (das aber erst CTranslate2 mit METAL-Unterstützung braucht auf dem Mac
    # bzw. CUDA auf Windows-Rechnern)
    try: 
        text = transcribe_whisper(audio)
        # return transcribe_jax(audio)
        # return transcribe_ws2t(audio)
        return text
    except:
        return ""

def transcribe_whisper(fname, model="large-v3-turbo"):
    # Vanilla Whisper. Womöglich nicht die schnellste Lösung. 
    stt = whisper.load_model(model)
    result = stt.transcribe(fname)
    return result['text']

def transcribe_jax(audio):
    # Nutzt nicht die Standard-Whisper-Bibliothek zum Transkribieren, 
    # sondern das verbesserte JAX - das beim ersten Durchlauf sehr langsam ist, 
    # weil es erst etwas herunterladen und übersetzen muss; danach geht's flotter. 
    # Installieren mit: 
    # pip install git+https://github.com/sanchit-gandhi/whisper-jax.git
    # Auch noch jax importieren? 
    #
    # Projektseite: https://github.com/sanchit-gandhi/whisper-jax
    # 
    # Das hier galt bei Whisper, bei whisper-jax noch prüfen: 
    # Speichert die Modelle unter ~/.cache/whisper/ ab; da auf meinem Mac schon Whisper-Modelle
    # geladen sind, nutze ich den zusätzlichen Parameter 
    # download_root="{path to the directory to download models}"
    from whisper_jax import FlaxWhisperPipline
    from typing import NamedType

    # instantiate pipeline
    pipeline = FlaxWhisperPipline("openai/whisper-large-v3-turbo")

    text = pipeline(audio)

    return text

import os
import whisper_s2t

def transcribe_ws2t(file_path, model_name="large-v3-turbo", output_format="txt"):
    """
    Transcribe an audio/video file using WhisperS2T.
    
    Args:
        file_path (str): Path to the .ogg or .mp4 file.
        model_name (str): Whisper model to use (e.g., "small", "medium", "large").
        output_format (str): Output format ("txt" or "json").
        
    Returns:
        str: Transcription text.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Initialize the WhisperS2T pipeline
    model = whisper_s2t.load_model(model_identifier="medium", backend='CTranslate2')
    files = [file_path]
    lang_codes = ['de']
    tasks = ['transcribe']
    initial_prompts = [None]

    out = model.transcribe_with_vad(files,
                                lang_codes=lang_codes,
                                tasks=tasks,
                                initial_prompts=initial_prompts,
                                batch_size=24)

    return out

