# transcribe.py
#
# Bilder mit GPT4o-mini in Bildbeschreibung umwandeln, 
# Audios/Videos lokal mit whisper transkribieren

import ollama
from openai import OpenAI
from pathlib import Path
import os
import whisper
import logging
from pydub import AudioSegment  # für die OGG-zu-MP4-Konversion

prompt = """Du bist Barrierefreiheits-Assistent.
Du erstellst eine deutsche Bildbeschreibung für den Alt-Text.
Beschreibe, was auf dem Bild zu sehen ist.
Beginne sofort mit der Beschreibung. Sei präzise und knapp.
Du erstellst eine deutsche Bildbeschreibung für den Alt-Text.  
Beschreibe, was auf dem Bild zu sehen ist. 
Beginne sofort mit der Beschreibung. Sei präzise und knapp. 
Wenn das Bild lesbaren Text enthält, zitiere diesen Text."""

# Use GPT-4 mini to describe images
OLLAMA = False

def gpt4_description(image_url):
    # Check a local image by converting it to b64: 
    # image_url = f"data:image/jpeg;base64, {b64_image}"
    print(".", end="")
    client = OpenAI(api_key = os.environ.get('OPENAI_API_KEY'))
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

def transcribe(fname, use_api = True):
    # Wrapper; ruft eine der drei Whisper-Transcribe-Varianten auf. 
    # Favorit: das beschleunigte whisper-s2t
    # (das aber erst CTranslate2 mit METAL-Unterstützung braucht auf dem Mac
    # bzw. CUDA auf Windows-Rechnern)
    #
    # Als erstes: Das in Telegram übliche .ogg-Audioformat konvertieren
    if ".ogg" in fname.lower():
        fname = convert_ogg_to_mp3(fname)
    try: 
        if use_api:
            text = transcribe_api(fname)
        else: 
            text = transcribe_whisper(fname)
        # return transcribe_jax(audio)
        # return transcribe_ws2t(audio)
        return text
    except:
        return ""


def convert_ogg_to_m4a(input_file):
    # Load the OGG file
    try:
        audio = AudioSegment.from_ogg(input_file)
        # Export the audio to an M4A file
        output_file = os.path.splitext(input_file)[0]+".m4a"
        audio.export(output_file, format="mp4")
        return output_file
    except:
        logging.error(f"Konnte Datei {input_file} nicht von OGG nach M4A wandeln")
        return None

def convert_ogg_to_mp3(input_file):
    # Load the OGG file
    try:
        audio = AudioSegment.from_ogg(input_file)
        # Export the audio to an M4A file
        output_file = os.path.splitext(input_file)[0]+".mp3"
        audio.export(output_file, format="mp3")
        return output_file
    except:
        logging.error(f"Konnte Datei {input_file} nicht von OGG nach MP3 wandeln")
        return None
    
def convert_mp4_to_mp3(input_file):
    # Load the video file
    try:
        audio = AudioSegment.from_file(input_file, format="mp4")
        # Export the audio to an MP3 file
        output_file = os.path.splitext(input_file)[0]+".mp3"
        audio.export(output_file, format="mp3")
        return output_file
    except:
        logging.error(f"Konnte Datei {input_file} nicht von MP4 nach MP3 wandeln")
        return None

def transcribe_api(fname):
    client = OpenAI()
    audio_file= open(fname, "rb")
    transcription = client.audio.transcriptions.create(
        model="whisper-1", 
        file=audio_file
    )
    return (transcription.text)


def transcribe_whisper(fname, model="large-v3-turbo"):
    # Vanilla Whisper. Womöglich nicht die schnellste Lösung. 
    # Installiere einfach mit 
    # pip install openai-whisper
    print(".",end="")
    stt = whisper.load_model(model)
    result = stt.transcribe(fname)
    return result['text']

# Hier fangen die Alternativ-Transcriber an. Sind auskommentiert, damit man den ganzen Kram
# nicht installieren muss, bevor das Paket losläuft. 
"""
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
    #
    from whisper_jax import FlaxWhisperPipline
    from typing import NamedType

    # instantiate pipeline
    pipeline = FlaxWhisperPipline("openai/whisper-large-v3-turbo")

    text = pipeline(audio)

    return text

# Library importieren mit
# pip install whisper-s2t
# oder
# pip install -U git+https://github.com/shashikg/WhisperS2T.git
#
# Problem mit Whisper: setzt auf dem Mac eine METAL-Einbindng voraus. 
# https://github.com/shashikg/WhisperS2T
import os
import whisper_s2t

def transcribe_ws2t(file_path, model_name="large-v3-turbo", output_format="txt"):
#    Transcribe an audio/video file using WhisperS2T.
#    
#    Args:
#       file_path (str): Path to the .ogg or .mp4 file.
#        model_name (str): Whisper model to use (e.g., "small", "medium", "large").
#        output_format (str): Output format ("txt" or "json").
#        
#    Returns:
#        str: Transcription text.
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

"""
